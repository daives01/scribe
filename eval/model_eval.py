import json
import os
import datetime
from typing import Optional
from pydantic import BaseModel, Field
from ollama import Client


# 1. Define the Schema using Pydantic
class EvaluationOutput(BaseModel):
    summary: str = Field(description="A summary of the transcript in 5 words or less")
    tag: str = Field(description="Must be one of: todo, note, misc")
    timestamp_rationale: str = Field(description="Explanation of timestamp calculation")
    timestamp: Optional[str] = Field(
        default=None,
        description="The task time in YYYY-MM-DDTHH:MM:SS format if applicable",
    )


def run_eval(config_path: str, model_name: str):
    # Setup client and file paths
    client = Client(host="http://100.94.163.58:11434")
    safe_model = model_name.replace(":", "-")
    base_name = os.path.splitext(os.path.basename(config_path))[0]
    output_file = f"{safe_model}-{base_name}-results.jsonl"

    # Load config
    with open(config_path, "r") as f:
        config = json.load(f)

    template = config["prompt_template"]
    transcripts = config["transcripts"]
    current_time = datetime.datetime.now().strftime("%A, %Y-%m-%dT%H:%M:%S")

    print(f"Starting Eval: {model_name} | Ref: {current_time}")

    with open(output_file, "a") as f_out:
        for i, text in enumerate(transcripts):
            print(f"[{i + 1}/{len(transcripts)}] Processing...", end=" ", flush=True)

            # Prepare prompt
            prompt = template.replace("{{transcript}}", text)
            prompt = prompt.replace("{{current_time}}", current_time)

            response = None
            try:
                # # 2. Try with structured output first
                # try:
                #     response = client.generate(
                #         model=model_name,
                #         prompt=prompt,
                #         format=EvaluationOutput.model_json_schema(),
                #     )
                #     # The response.response field should now strictly contain valid JSON
                #     output_data = EvaluationOutput.model_validate_json(
                #         response.response
                #     )
                # except:
                #     # Fallback: Call without structured output and parse JSON from response
                response = client.generate(
                    model=model_name,
                    prompt=prompt,
                )
                # Try to extract JSON from the response
                json_str = response.response.strip()
                if json_str.startswith("```json"):
                    json_str = json_str[7:-3].strip()
                elif json_str.startswith("```"):
                    json_str = json_str[3:-3].strip()

                # Find the last JSON object in the response
                import re

                json_match = re.search(r"\{[^{}]*\}(?=[^{}]*$)", json_str)
                if json_match:
                    json_str = json_match.group()

                output_data = EvaluationOutput.model_validate_json(json_str)

                result = {"input": text, "output": output_data.model_dump()}
                print("Success")

            except Exception as e:
                print(f"Failed: {str(e)}")
                result = {
                    "input": text,
                    "output": {
                        "error": "failed",
                        "raw": response.response if response else str(e),
                    },
                }

            f_out.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python model_eval.py <config.json> <model_name>")
    else:
        run_eval(sys.argv[1], sys.argv[2])
