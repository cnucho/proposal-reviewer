REQUIRED_DIRECTORIES = [
    "raw/proposals",
    "raw/rfp",
    "requests",
    "results",
    "prompts",
    "state",
    "schemas",
]

REQUIRED_FILES = [
    "state/workspace.json",
]

PLACEHOLDER_FILES = {
    "schemas/review_request_v1.schema.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewRequestV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "id",
    "title",
    "proposal_ref",
    "rfp_ref",
    "proposal_excerpt",
    "rfp_excerpt",
    "evaluation_focus",
    "created_at"
  ],
  "properties": {
    "schema_version": { "const": "ReviewRequestV1" },
    "id": { "type": "string" },
    "title": { "type": "string" },
    "proposal_ref": { "type": "string" },
    "rfp_ref": { "type": "string" },
    "proposal_excerpt": { "type": "string" },
    "rfp_excerpt": { "type": "string" },
    "evaluation_focus": {
      "type": "array",
      "items": { "type": "string" }
    },
    "created_at": { "type": "string" }
  }
}
""",
    "schemas/review_result_v1.schema.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewResultV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "id",
    "request_id",
    "verdict",
    "scorecard",
    "strengths",
    "findings",
    "required_revisions",
    "reviewer_summary"
  ],
  "properties": {
    "schema_version": { "const": "ReviewResultV1" },
    "id": { "type": "string" },
    "request_id": { "type": "string" },
    "verdict": { "type": "string", "enum": ["pass", "warn", "fail"] },
    "scorecard": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["label", "score", "max_score"],
        "properties": {
          "label": { "type": "string" },
          "score": { "type": "integer" },
          "max_score": { "type": "integer" }
        }
      }
    },
    "strengths": { "type": "array", "items": { "type": "string" } },
    "findings": { "type": "array", "items": { "type": "string" } },
    "required_revisions": { "type": "array", "items": { "type": "string" } },
    "reviewer_summary": { "type": "string" }
  }
}
""",
}
