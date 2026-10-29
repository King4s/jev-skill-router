//! OpenAI Decisions wire translation; ranking still uses the shared validator.
use anyhow::{bail, Result};
use serde_json::{json, Map, Value};

pub fn request(source: &Value) -> Result<Value> {
    let questions = source["questions"]
        .as_object()
        .ok_or_else(|| anyhow::anyhow!("Invalid internal questions"))?;
    let mut converted = Vec::new();
    for (name, question) in questions {
        let criteria = question["criteria"]
            .as_array()
            .ok_or_else(|| anyhow::anyhow!("Invalid internal rubric"))?;
        let levels: Vec<Value> = criteria
            .iter()
            .map(|label| json!({"label": label}))
            .collect();
        converted.push(json!({"name":name,"type":"score","levels":levels,
            "instructions":serde_json::to_string(&question["instructions"])?}));
    }
    Ok(json!({"model": source["model"],
        "input":[{"role":"user","content":[{"type":"input_json","data":source["state"]}]}],
        "questions":converted}))
}

pub fn normalize(mut response: Value, expected: &Value) -> Result<Value> {
    let answers = response["answers"]
        .as_array()
        .ok_or_else(|| anyhow::anyhow!("OpenAI returned an invalid answers envelope"))?;
    let questions = expected["questions"]
        .as_object()
        .ok_or_else(|| anyhow::anyhow!("Invalid internal questions"))?;
    let mut normalized = Map::new();
    for answer in answers {
        let name = answer["name"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("OpenAI returned an unnamed answer"))?;
        if !questions.contains_key(name) || normalized.contains_key(name) {
            bail!("OpenAI returned duplicate or unexpected answer IDs");
        }
        let mut answer = answer.clone();
        if answer["type"] == "score" {
            let levels = questions[name]["criteria"].as_array().unwrap();
            let mut probabilities = Map::new();
            let valid = answer["probabilities"].as_array().is_some_and(|entries| {
                entries.len() == levels.len()
                    && entries.iter().all(|entry| {
                        let Some(index) = entry["value"]
                            .as_u64()
                            .and_then(|i| usize::try_from(i).ok())
                        else {
                            return false;
                        };
                        if index >= levels.len()
                            || entry["label"] != levels[index]
                            || probabilities.contains_key(&index.to_string())
                        {
                            return false;
                        }
                        probabilities.insert(index.to_string(), entry["probability"].clone());
                        true
                    })
            });
            answer["probabilities"] = if valid {
                Value::Object(probabilities)
            } else {
                Value::Null
            };
        }
        normalized.insert(name.to_owned(), answer);
    }
    response["answers"] = Value::Object(normalized);
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source() -> Value {
        crate::jev::payload(
            "Build a dashboard",
            &[json!({"name":"dashboard"})],
            "gpt-6-luna",
        )
    }

    fn answer() -> Value {
        let source = source();
        let levels = source["questions"]["skill_000"]["criteria"]
            .as_array()
            .unwrap();
        let probabilities: Vec<Value> = levels.iter().enumerate().map(|(i, label)| {
            json!({"value":i,"label":label,"probability":if i == 3 {1.0} else {0.0}})
        }).collect();
        json!({"name":"skill_000","type":"score","score":3.0,"confidence":0.8,"probabilities":probabilities})
    }

    #[test]
    fn wire_contract_preserves_rubric_state_and_metadata() {
        let source = source();
        let request = request(&source).unwrap();
        assert!(request.get("state").is_none());
        assert_eq!(request["input"][0]["content"][0]["data"], source["state"]);
        assert_eq!(request["questions"][0]["name"], "skill_000");
        assert!(request["questions"][0]["instructions"].is_string());
        assert_eq!(
            request["questions"][0]["levels"][3]["label"],
            source["questions"]["skill_000"]["criteria"][3]
        );
        let response = normalize(
            json!({"answers":[answer()],"model":"gpt-6-luna","usage":{"input_tokens":10}}),
            &source,
        )
        .unwrap();
        assert_eq!(response["model"], "gpt-6-luna");
        assert_eq!(response["usage"]["input_tokens"], 10);
        assert!(crate::jev::validate_score(&response["answers"]["skill_000"]).is_none());
    }

    #[test]
    fn invalid_names_fail_and_refusals_are_not_scores() {
        let source = source();
        assert!(normalize(json!({"answers":[answer(),answer()]}), &source).is_err());
        for name in [Value::Null, json!("unknown")] {
            assert!(
                normalize(json!({"answers":[{"name":name,"type":"refusal"}]}), &source).is_err()
            );
        }
        let response = normalize(
            json!({"answers":[{"name":"skill_000","type":"refusal"}]}),
            &source,
        )
        .unwrap();
        assert!(crate::jev::validate_score(&response["answers"]["skill_000"]).is_some());
    }

    #[test]
    fn duplicate_indices_and_inconsistent_scores_remain_invalid() {
        let source = source();
        for broken in [
            json!({}),
            json!([]),
            json!(vec![answer()["probabilities"][0].clone(); 4]),
        ] {
            let mut answer = answer();
            answer["probabilities"] = broken;
            let response = normalize(json!({"answers":[answer]}), &source).unwrap();
            assert!(crate::jev::validate_score(&response["answers"]["skill_000"]).is_some());
        }
        let mut answer = answer();
        answer["score"] = json!(0);
        let response = normalize(json!({"answers":[answer]}), &source).unwrap();
        assert!(crate::jev::validate_score(&response["answers"]["skill_000"]).is_some());
    }
}
