from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict
from tavily import TavilyClient
from dotenv import load_dotenv
import os
from prompts import Prompts
from llm import r1
import json
load_dotenv()

class GraphState(TypedDict):
    question: str
    retrieved_context: str
    router_decision: str
    answer_to_question: str
    missing_information: str
    reasoning: str
    useful_information: str

class QAAgent:
    def __init__(self):
        self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        self.workflow = self.create_workflow()

    def retrieve(self, state: GraphState):
        print("\n=== STEP 1: RETRIEVAL ===")
        question = state["question"]
        print("Searching for:", question)
        result = self.tavily_client.search(question, max_results=3)    
        retrieved_context = "\n".join([r["content"] for r in result["results"]])
        print("Retrieved Context: \n", retrieved_context)
        return {"retrieved_context": retrieved_context}

    def validate_retrieval(self, state: GraphState):
        print("\n=== STEP 2: VALIDATION ===")
        question = state["question"]
        retrieved_context = state["retrieved_context"]
        
        validation_chain = Prompts.VALIDATE_RETRIEVAL | r1
        llm_output = validation_chain.invoke({"retrieved_context": retrieved_context, "question": question}).content
        
        if "<think>" in llm_output and "</think>" in llm_output:
            reasoning = llm_output.split("<think>")[1].split("</think>")[0].strip()
            response = llm_output.split("</think>")[1].strip()
        else:
            reasoning = ""
            response = llm_output.strip()  # 将整个输出当作 response

        strcutured_response = json.loads(response)
        
        router_decision = strcutured_response["status"]
        missing_information = strcutured_response["missing_information"]
        useful_information = strcutured_response["useful_information"]
        print("router decision:", router_decision)
        print("missing information:", missing_information)
        print("useful information:", useful_information)

        if router_decision == "INCOMPLETE":
            print("Missing Information:", missing_information)

        return {"router_decision": router_decision, "retrieved_context": retrieved_context, "useful_information": useful_information, "missing_information": missing_information, "reasoning": reasoning}

    def answer(self, state: GraphState):
        print("\n=== STEP 3: ANSWERING ===")
        question = state["question"]
        context = state["retrieved_context"]

        answer_chain = Prompts.ANSWER_QUESTION | r1
        llm_output = answer_chain.invoke({"retrieved_context": context, "question": question}).content
        
        # 检查 <think> 标签是否存在
        if "<think>" in llm_output and "</think>" in llm_output:
            reasoning = llm_output.split("<think>")[1].split("</think>")[0].strip()
            answer = llm_output.split("</think>")[1].strip()
        else:
            reasoning = ""
            answer = llm_output.strip()  # 将整个输出当作 answer

        return {"answer_to_question": answer}

    def find_missing_information(self, state: GraphState):
        print("\n=== STEP 2b: FINDING MISSING INFORMATION ===")
        missing_information = state["missing_information"]
        print("Searching for:", missing_information)
        
        tavily_query = self.tavily_client.search(missing_information, max_results=3)
        previously_retrieved_useful_information = state["useful_information"]
        newly_retrieved_context = "\n".join([r["content"] for r in tavily_query["results"]])
        combined_context = f"{previously_retrieved_useful_information}\n{newly_retrieved_context}"
        print("newly retrieved context:", newly_retrieved_context)
        return {"retrieved_context": combined_context}

    @staticmethod
    def decide_route(state: GraphState):
        return state["router_decision"]


    # def create_workflow(self):
    #     workflow = StateGraph(GraphState)
        
    #     workflow.add_node("retrieve context", self.retrieve)
    #     workflow.add_node("answer", self.answer)
        
    #     workflow.set_entry_point("retrieve context")
    #     workflow.add_edge("retrieve context","answer")
    #     workflow.add_edge("answer", END)
    #     compiled_graph = workflow.compile()
    #     compiled_graph.get_graph(xray=1).draw_mermaid_png(output_file_path="agent-architecture.png")
    #     return compiled_graph

    def create_workflow(self):
        workflow = StateGraph(GraphState)
        
        workflow.add_node("retrieve context", self.retrieve)
        workflow.add_node("is retrieved context complete?", self.validate_retrieval)
        workflow.add_node("answer", self.answer)
        workflow.add_node("find missing information", self.find_missing_information)
        
        workflow.set_entry_point("retrieve context")
        workflow.add_edge("retrieve context", "is retrieved context complete?")
        
        workflow.add_conditional_edges(
            "is retrieved context complete?",
            self.decide_route,
            {
                "COMPLETE": "answer",
                "INCOMPLETE": "find missing information"
            }
        )
        workflow.add_edge("find missing information", "is retrieved context complete?")
    
        workflow.add_edge("answer", END)
        compiled_graph = workflow.compile()
        compiled_graph.get_graph(xray=1).draw_mermaid_png(output_file_path="agent-architecture.png")
        return compiled_graph


    

    def run(self, question: str):
        result = self.workflow.invoke({"question": question})
        return result["answer_to_question"]

if __name__ == "__main__":
    agent = QAAgent()
    answer = agent.run("《哪吒2》中哪吒的师傅的师傅是谁?")
    print(answer)