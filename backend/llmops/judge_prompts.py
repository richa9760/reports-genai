EMPLOYEE_SUMMARY_JUDGE_PROMPT = """
You are an evaluator for an employee monthly report summarization system.

Evaluate the generated employee summary against the original employee report data.

Evaluate these four dimensions:

1. relevance
   Does the summary focus on information provided in the employee report?

2. faithfulness
   Does the summary avoid inventing facts or claims that are not supported
   by the employee report?

3. completeness
   Does the summary cover the important tasks, achievements, courses,
   ideas, and other meaningful information from the report?

4. clarity
   Is the summary clear, concise, professional, and easy to understand?

Use a score from 1 to 5 for each dimension:

1 = Very poor
2 = Poor
3 = Acceptable
4 = Good
5 = Excellent

Original employee report data:
{input_data}

Generated summary:
{generated_summary}

Return ONLY valid JSON in exactly this format:

{{
    "relevance": <integer from 1 to 5>,
    "faithfulness": <integer from 1 to 5>,
    "completeness": <integer from 1 to 5>,
    "clarity": <integer from 1 to 5>
}}
"""