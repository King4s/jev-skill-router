use anyhow::{bail, Result};
use serde::Deserialize;
use std::{collections::BTreeMap, io::Read};

const FILE_LIMIT: usize = 65536;
const PROFILE_LIMIT: usize = 32;

#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum WireFormat {
    #[default]
    Systemone,
    OpenaiDecisions,
}

pub struct Provider {
    pub name: String,
    pub endpoint: String,
    pub model: String,
    pub key: String,
    pub wire_format: WireFormat,
    pub fallback: Option<Box<Provider>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    default: String,
    fallback: Option<String>,
    profiles: BTreeMap<String, Profile>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Profile {
    endpoint: String,
    model: String,
    key_env: String,
    endpoint_env: Option<String>,
    model_env: Option<String>,
    #[serde(default)]
    wire_format: WireFormat,
}

fn identifier(s: &str, environment: bool) -> bool {
    let first = |b: u8| {
        if environment {
            b.is_ascii_uppercase() || b == b'_'
        } else {
            b.is_ascii_lowercase()
        }
    };
    !s.is_empty()
        && s.len() <= if environment { 128 } else { 64 }
        && first(s.as_bytes()[0])
        && s.bytes()
            .all(|b| first(b) || b.is_ascii_digit() || (!environment && b"_-".contains(&b)))
}

fn validate_endpoint(endpoint: &str) -> Result<()> {
    let url =
        reqwest::Url::parse(endpoint).map_err(|_| anyhow::anyhow!("Invalid provider endpoint"))?;
    let authority = endpoint
        .split("://")
        .nth(1)
        .unwrap_or("")
        .split('/')
        .next()
        .unwrap_or("");
    let loopback = url.host_str().is_some_and(|host| {
        host == "localhost"
            || host
                .trim_matches(['[', ']'])
                .parse::<std::net::IpAddr>()
                .is_ok_and(|ip| ip.is_loopback())
    });
    if endpoint.len() > 2048
        || !(endpoint.starts_with("https://") || endpoint.starts_with("http://"))
        || endpoint.contains('\\')
        || endpoint
            .bytes()
            .any(|b| b.is_ascii_whitespace() || b.is_ascii_control())
        || authority.contains('@')
        || !url.username().is_empty()
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
        || url.host_str().is_none()
        || !(url.scheme() == "https" || (url.scheme() == "http" && loopback))
    {
        bail!("Unsafe provider endpoint; HTTPS or loopback HTTP without credentials, query or fragment is required");
    }
    Ok(())
}

fn validate_model(model: &str) -> Result<()> {
    if model.is_empty()
        || model.len() > 128
        || model.chars().any(|c| c.is_whitespace() || c.is_control())
    {
        bail!("Invalid provider model identifier");
    }
    Ok(())
}

impl Provider {
    pub fn require_ready(&self) -> Result<()> {
        if self.model.is_empty() {
            bail!("Provider model is required; install decision-providers.json or set JEV_MODEL for legacy Jev");
        }
        if self.key.is_empty() {
            bail!("Selected provider API key is required for ranking");
        }
        if self.wire_format == WireFormat::OpenaiDecisions && self.model != "gpt-6-luna" {
            bail!("OpenAI Decisions currently supports only gpt-6-luna");
        }
        Ok(())
    }
}

fn select(bytes: Option<&[u8]>, env: impl Fn(&str) -> Option<String>) -> Result<Provider> {
    select_env(bytes, &env)
}

fn select_env(bytes: Option<&[u8]>, env: &dyn Fn(&str) -> Option<String>) -> Result<Provider> {
    let (name, profile, fallback_name) = if let Some(bytes) = bytes {
        if bytes.len() > FILE_LIMIT {
            bail!("Provider configuration exceeds 64 KiB");
        }
        let mut config: Config = serde_json::from_slice(bytes)
            .map_err(|_| anyhow::anyhow!("Invalid provider configuration"))?;
        if config.profiles.is_empty()
            || config.profiles.len() > PROFILE_LIMIT
            || !identifier(&config.default, false)
            || !config.profiles.contains_key(&config.default)
        {
            bail!("Invalid provider profile count or default");
        }
        if config.fallback.as_ref().is_some_and(|name| {
            name == &config.default
                || !identifier(name, false)
                || !config.profiles.contains_key(name)
        }) {
            bail!("Invalid configured fallback provider");
        }
        for (name, p) in &config.profiles {
            if !identifier(name, false)
                || !identifier(&p.key_env, true)
                || [p.endpoint_env.as_ref(), p.model_env.as_ref()]
                    .into_iter()
                    .flatten()
                    .any(|v| !identifier(v, true))
            {
                bail!("Invalid provider profile or environment identifier");
            }
            validate_endpoint(&p.endpoint)?;
            validate_model(&p.model)?;
        }
        let explicit = env("SKILL_ROUTER_PROVIDER");
        let fallback_name = if explicit.is_none() {
            config.fallback
        } else {
            None
        };
        let name = explicit.unwrap_or(config.default);
        if !identifier(&name, false) {
            bail!("Invalid selected provider identifier");
        }
        let profile = config
            .profiles
            .remove(&name)
            .ok_or_else(|| anyhow::anyhow!("Selected provider is not configured"))?;
        (name, profile, fallback_name)
    } else {
        let name = env("SKILL_ROUTER_PROVIDER").unwrap_or_else(|| "jev".into());
        if name != "jev" {
            bail!("Selected provider requires a configuration file");
        }
        (
            name,
            Profile {
                endpoint: "https://api.typesafe.ai/v1/systemone".into(),
                model: String::new(),
                key_env: "TYPESAFE_API_KEY".into(),
                endpoint_env: Some("JEV_API".into()),
                model_env: Some("JEV_MODEL".into()),
                wire_format: WireFormat::Systemone,
            },
            None,
        )
    };
    let endpoint = profile
        .endpoint_env
        .as_ref()
        .and_then(|name| env(name))
        .unwrap_or(profile.endpoint);
    let model = profile
        .model_env
        .as_ref()
        .and_then(|name| env(name))
        .unwrap_or(profile.model);
    validate_endpoint(&endpoint)?;
    if bytes.is_some() || !model.is_empty() {
        validate_model(&model)?;
    }
    let key = env(&profile.key_env).unwrap_or_default();
    if !key.is_empty()
        && (key.len() > 8192
            || !key.bytes().all(|b| b.is_ascii_graphic())
            || reqwest::header::HeaderValue::from_str(&format!("Bearer {key}")).is_err())
    {
        bail!("Invalid selected provider API key header");
    }
    let fallback = fallback_name
        .map(|name| {
            select_env(bytes, &|key| {
                if key == "SKILL_ROUTER_PROVIDER" {
                    Some(name.clone())
                } else {
                    env(key)
                }
            })
            .map(Box::new)
        })
        .transpose()?;
    Ok(Provider {
        name,
        endpoint,
        model,
        key,
        wire_format: profile.wire_format,
        fallback,
    })
}

pub fn load() -> Result<Provider> {
    let path = std::env::var_os("SKILL_ROUTER_PROVIDERS_FILE");
    let file = std::fs::File::open(
        path.as_deref()
            .unwrap_or_else(|| std::ffi::OsStr::new("decision-providers.json")),
    );
    let bytes = match file {
        Ok(file) => {
            let mut bytes = Vec::new();
            file.take((FILE_LIMIT + 1) as u64)
                .read_to_end(&mut bytes)
                .map_err(|_| anyhow::anyhow!("Cannot read provider configuration"))?;
            Some(bytes)
        }
        Err(e) if path.is_none() && e.kind() == std::io::ErrorKind::NotFound => None,
        Err(_) => bail!("Cannot open provider configuration"),
    };
    select(bytes.as_deref(), |name| match std::env::var(name) {
        Ok(value) => Some(value),
        Err(std::env::VarError::NotPresent) => None,
        // Preserve explicit invalid overrides as a refusal, never as an absent value.
        Err(std::env::VarError::NotUnicode(_)) => Some("\0".into()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env<'a>(pairs: &'a [(&'a str, &'a str)]) -> impl Fn(&str) -> Option<String> + 'a {
        move |name| {
            pairs
                .iter()
                .find(|(k, _)| *k == name)
                .map(|(_, v)| (*v).into())
        }
    }

    #[test]
    fn custom_profile_and_explicit_overrides_need_no_code_changes() {
        let config = br#"{"default":"company","profiles":{"company":{"endpoint":"https://decisions.example/v1/evaluate","model":"company-model","key_env":"COMPANY_KEY","endpoint_env":"COMPANY_URL","model_env":"COMPANY_MODEL"}}}"#;
        let p = select(
            Some(config),
            env(&[("COMPANY_KEY", "custom-key"), ("JEV_MODEL", "ignored")]),
        )
        .unwrap();
        assert_eq!(
            (&*p.name, &*p.model, &*p.key),
            ("company", "company-model", "custom-key")
        );
        let p = select(
            Some(config),
            env(&[
                ("COMPANY_URL", "http://127.0.0.1:8000/offline"),
                ("COMPANY_MODEL", "other-model"),
            ]),
        )
        .unwrap();
        assert_eq!(p.endpoint, "http://127.0.0.1:8000/offline");
        assert_eq!(p.model, "other-model");
        assert!(p.require_ready().is_err());
        let no_opt_in = br#"{"default":"custom","profiles":{"custom":{"endpoint":"https://custom.example/decisions","model":"custom-model","key_env":"CUSTOM_KEY"}}}"#;
        let p = select(
            Some(no_opt_in),
            env(&[
                ("JEV_API", "unsafe"),
                ("JEV_MODEL", "ignored"),
                ("TYPESAFE_API_KEY", "wrong-key"),
            ]),
        )
        .unwrap();
        assert_eq!(p.endpoint, "https://custom.example/decisions");
        assert_eq!(p.model, "custom-model");
        assert!(p.key.is_empty());
    }

    #[test]
    fn configured_model_tokens_are_literal_and_bounded() {
        use serde_json::json;
        let config = json!({"default":"custom","profiles":{"custom":{"endpoint":"https://custom.example/decisions","model":"custom-model","key_env":"CUSTOM_KEY","model_env":"CUSTOM_MODEL"}}});
        let bytes = serde_json::to_vec(&config).unwrap();
        for model in [
            "custom-model",
            "~typesafe/jev-latest",
            "@company/model+revision=2",
            r#"部署/モデル:"v2"\preview"#,
            &"a".repeat(128),
            &"é".repeat(64),
        ] {
            let mut literal = config.clone();
            literal["profiles"]["custom"]["model"] = json!(model);
            for p in [
                select(Some(&serde_json::to_vec(&literal).unwrap()), env(&[])).unwrap(),
                select(Some(&bytes), env(&[("CUSTOM_MODEL", model)])).unwrap(),
            ] {
                assert_eq!(p.model, model);
                let body =
                    serde_json::to_vec(&crate::jev::payload("project", &[], &p.model)).unwrap();
                let body: serde_json::Value = serde_json::from_slice(&body).unwrap();
                assert_eq!(body["model"], model);
            }
        }
        for model in [
            "",
            " model",
            "model ",
            "model\tv2",
            "model\n",
            "model\u{a0}v2",
            "model\u{2003}v2",
            "model\0",
            "model\u{7f}",
            "model\u{80}",
            &"a".repeat(129),
            &format!("{}a", "é".repeat(64)),
        ] {
            let mut literal = config.clone();
            literal["profiles"]["custom"]["model"] = json!(model);
            assert!(select(Some(&serde_json::to_vec(&literal).unwrap()), env(&[])).is_err());
            assert!(select(Some(&bytes), env(&[("CUSTOM_MODEL", model)])).is_err());
        }
    }

    #[test]
    fn legacy_requires_explicit_model_and_config_has_precedence() {
        let pairs = [
            ("JEV_API", "http://[::1]:9999/decisions"),
            ("JEV_MODEL", "explicit-model"),
            ("TYPESAFE_API_KEY", "legacy-key"),
        ];
        let p = select(None, env(&pairs)).unwrap();
        assert_eq!(
            (&*p.name, &*p.model, &*p.key),
            ("jev", "explicit-model", "legacy-key")
        );
        assert_eq!(p.endpoint, pairs[0].1);
        assert!(p.require_ready().is_ok());
        let p = select(None, env(&[])).unwrap();
        assert!(p.model.is_empty());
        assert!(p.require_ready().is_err());
        let p = select(
            Some(include_bytes!("../decision-providers.json")),
            env(&pairs),
        )
        .unwrap();
        assert_eq!(p.model, "explicit-model");
        assert_eq!(p.endpoint, pairs[0].1);
        assert!(select(None, env(&[("SKILL_ROUTER_PROVIDER", "perplexity")])).is_err());
    }

    #[test]
    fn selected_missing_key_never_falls_back_or_reads_unused_keys() {
        let reads = std::cell::RefCell::new(Vec::new());
        let p = select(Some(include_bytes!("../decision-providers.json")), |name| {
            reads.borrow_mut().push(name.to_owned());
            match name {
                "SKILL_ROUTER_PROVIDER" => Some("perplexity".into()),
                "TYPESAFE_API_KEY" => panic!("unused key must not be consulted"),
                _ => None,
            }
        })
        .unwrap();
        assert_eq!(p.name, "perplexity");
        assert!(p.key.is_empty());
        assert!(p.require_ready().is_err());
        assert_eq!(
            *reads.borrow(),
            vec!["SKILL_ROUTER_PROVIDER", "PERPLEXITY_API_KEY"]
        );
        let p = select(
            Some(include_bytes!("../decision-providers.json")),
            env(&[
                ("TYPESAFE_API_KEY", "valid"),
                ("PERPLEXITY_API_KEY", "unused\r\nsecret"),
            ]),
        )
        .unwrap();
        assert!(p.require_ready().is_ok());
    }

    #[test]
    fn config_limits_identifiers_and_errors_are_secret_safe() {
        use serde_json::json;
        let config = json!({"default":"custom","profiles":{"custom":{"endpoint":"https://custom.example/decisions","model":"custom-model","key_env":"CUSTOM_KEY"}}});
        for (field, bad) in [
            ("endpoint", "http://remote.example/secret"),
            ("endpoint", "https://user:secret@custom.example/decisions"),
            ("endpoint", "https://custom.example/decisions?key=secret"),
            ("endpoint", "https://custom.example/decisions#secret"),
            ("endpoint", "not-a-url-secret"),
            ("model", "secret\r\n"),
            ("key_env", "secret-key"),
        ] {
            let mut bad_config = config.clone();
            bad_config["profiles"]["custom"][field] = json!(bad);
            let bytes = serde_json::to_vec(&bad_config).unwrap();
            let error = select(Some(&bytes), env(&[])).err().unwrap().to_string();
            assert!(!error.contains(bad));
            assert!(!error.contains("secret"));
        }
        for name in ["missing", "../secret", "", "Custom", "with space"] {
            assert!(select(
                Some(&serde_json::to_vec(&config).unwrap()),
                env(&[("SKILL_ROUTER_PROVIDER", name)])
            )
            .is_err());
        }
        let mut config = config;
        config["default"] = json!("unknown");
        assert!(select(Some(&serde_json::to_vec(&config).unwrap()), env(&[])).is_err());
        assert!(select(Some(&vec![b' '; FILE_LIMIT + 1]), env(&[])).is_err());
        assert!(select(Some(b"{\"profiles\":{}}"), env(&[])).is_err());
        assert!(select(Some(b"invalid secret JSON"), env(&[]))
            .err()
            .unwrap()
            .to_string()
            .eq("Invalid provider configuration"));
        let profiles: BTreeMap<_, _> = (0..=PROFILE_LIMIT)
            .map(|i| (format!("profile{i}"), config["profiles"]["custom"].clone()))
            .collect();
        let bytes = serde_json::to_vec(&json!({"default":"profile0","profiles":profiles})).unwrap();
        assert!(select(Some(&bytes), env(&[])).is_err());
        for bad in ["bad\r\nsecret", "bad secret", "nonascii-é"] {
            let error = select(
                None,
                env(&[("JEV_MODEL", "model"), ("TYPESAFE_API_KEY", bad)]),
            )
            .err()
            .unwrap()
            .to_string();
            assert_eq!(error, "Invalid selected provider API key header");
        }
    }

    #[test]
    fn endpoint_boundary_is_https_or_literal_loopback_only() {
        for good in [
            "https://api.example/decisions",
            "http://localhost:9000/decisions",
            "http://127.0.0.2/decisions",
            "http://[::1]/decisions",
        ] {
            assert!(validate_endpoint(good).is_ok(), "{good}");
        }
        for bad in [
            "http://localhost.example/",
            "http://192.168.1.1/",
            "http://[::ffff:192.168.1.1]/",
            "ftp://localhost/",
            "https://@example.com/",
            "https://example.com/?",
            "https://example.com/#",
            " https://example.com/",
            "https://example.com/\n",
            "https:\\\\@example.com/",
            "https:example.com/",
        ] {
            assert!(validate_endpoint(bad).is_err());
        }
        assert!(validate_model(&"a".repeat(129)).is_err());
        assert!(validate_endpoint(&format!("https://example.com/{}", "a".repeat(2048))).is_err());
    }

    #[test]
    fn selects_configured_operators_and_only_their_keys() {
        let bytes = include_bytes!("../decision-providers.json");
        let p = select(Some(bytes), env(&[("TYPESAFE_API_KEY", "jev-key")])).unwrap();
        assert_eq!(
            (&*p.name, &*p.model, &*p.key),
            ("jev", "jev-latest", "jev-key")
        );
        let p = select(
            Some(bytes),
            env(&[
                ("SKILL_ROUTER_PROVIDER", "perplexity"),
                ("PERPLEXITY_API_KEY", "pplx-key"),
                ("TYPESAFE_API_KEY", "wrong-key"),
                ("JEV_API", "https://wrong.example/endpoint"),
                ("JEV_MODEL", "wrong-model"),
            ]),
        )
        .unwrap();
        assert_eq!(
            (&*p.name, &*p.model, &*p.key),
            ("perplexity", "pplx-decider-v1.1-27b", "pplx-key")
        );
        assert_eq!(p.endpoint, "https://api.perplexity.ai/v1/decisions");
    }

    #[test]
    fn default_has_openai_standby_but_explicit_selection_is_strict() {
        let bytes = include_bytes!("../decision-providers.json");
        let provider = select(
            Some(bytes),
            env(&[
                ("TYPESAFE_API_KEY", "primary"),
                ("OPENAI_API_KEY", "standby"),
            ]),
        )
        .unwrap();
        assert_eq!(provider.name, "jev");
        let fallback = provider.fallback.unwrap();
        assert_eq!(fallback.name, "openai");
        assert_eq!(fallback.wire_format, WireFormat::OpenaiDecisions);
        assert_eq!(fallback.key, "standby");
        let provider = select(Some(bytes), |name| match name {
            "SKILL_ROUTER_PROVIDER" => Some("jev".into()),
            "TYPESAFE_API_KEY" => Some("primary".into()),
            "OPENAI_API_KEY" => panic!("Explicit selection must not load standby credentials"),
            _ => None,
        })
        .unwrap();
        assert!(provider.fallback.is_none());
    }

    #[test]
    fn fallback_must_be_distinct_and_configured() {
        for fallback in ["missing", "jev", "../bad"] {
            let mut config: serde_json::Value =
                serde_json::from_slice(include_bytes!("../decision-providers.json")).unwrap();
            config["fallback"] = serde_json::json!(fallback);
            assert!(select(Some(&serde_json::to_vec(&config).unwrap()), env(&[])).is_err());
        }
    }
}
