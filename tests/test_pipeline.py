from step_in_line.step import step
from step_in_line.pipeline import Pipeline


def test_pipeline_creates_step_dag():
    @step
    def preprocess(arg1: str) -> str:
        return "hello"

    @step
    def preprocess_2(arg1: str) -> str:
        return "hello"

    @step
    def preprocess_3(arg1: str) -> str:
        return "hello"

    @step
    def train(arg2: str):
        return "goodbye"

    step_process_result = preprocess("hi")
    step_process_result_2 = preprocess_2(step_process_result)
    step_process_result_3 = preprocess_3(step_process_result)
    step_train_result = train(
        step_process_result, step_process_result_2, step_process_result_3
    )

    pipe = Pipeline("mytest", steps=[step_train_result])
    assert len(pipe.generate_step_functions().states.keys()) == 3
