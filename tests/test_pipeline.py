from step_in_line.step import step
from step_in_line.pipeline import PipelineG


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

    pipe = PipelineG("mytest", steps=[step_train_result])
    pipe.generate_step_functions()
    # this works if everything needs to happen sequentially, but not efficient if things can run in parallel
    # print(list(nx.topological_sort(pipe.graph)))
    # print(list(nx.topological_sort(nx.line_graph(pipe.graph))))

    ## to actually get by "index" or "Depth"
    # print("TOP GENERATIONS")
    # print(list(nx.topological_generations(pipe.graph)))

    assert False
