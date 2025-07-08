##################################### ------ {Web search Integrated - Live Agent} ------#####################################
import os
import asyncio
import logging
from typing import Dict, List, Any, TypedDict
from datetime import datetime
from datetime import datetime, timezone

from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from openai import OpenAI

# Setup dedicated logger for this class
logger = logging.getLogger("general_expert_agent")
logger.setLevel(logging.INFO)

# Ensure no duplicate handlers if imported multiple times
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [GeneralExpertAgent] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# class GeneralExpertState(TypedDict):
#     expert_names: List[str]
#     summaries: List[Dict[str, Any]]
#     final_output: str

class GeneralExpertState(TypedDict):
    expert_names: List[str]
    summaries: List[Dict[str, Any]]
    time_frame: str
    focus_areas: List[str]
    final_output: str


class GeneralExpertAgent:
    def __init__(self, api_key: str):
        logger.info("Initializing GeneralExpertAgent with OpenAI client.")
        self.llm = OpenAI(api_key=api_key)

    def create_general_expert_agent(self) -> StateGraph:
        def analyze_experts(state: GeneralExpertState) -> GeneralExpertState:
            summaries = []
            logger.info(f"Starting analysis for experts: {state['expert_names']} with time frame: {state['time_frame']} and focus_areas: {state['focus_areas']}")

            # prompt_template = """
            # Identify the person's core expertise and deliver exactly one section in BULLET POINTS:

            # **Key views & insights (past 7 days)**
            # ▪ 5 bullets only
            # ▪ Each bullet: state the insight (short but informative and relevant for an investor)
            # ▪ Include inline citations with source URLs in brackets for each bullet

            # Expert: {expert_name}
            # Time window: {time_frame}
            # """
            prompt_template = """
                Identify the person's core expertise and deliver exactly one section in BULLET POINTS.

                **Key views & insights ({time_frame})**
                ▪ Focus only on these areas: {focus_areas}
                ▪ 5 bullets only
                ▪ Each bullet: state the insight (short but informative and relevant for an investor)
                ▪ Include inline citations with source URLs in brackets for each bullet

                Expert: {expert_name}
                Time window: {time_frame}
                Focus Areas: {focus_areas}
            """


            for expert in state['expert_names']:
                logger.info(f"Processing expert: {expert} for time_frame: {state['time_frame']} with focus_areas: {state['focus_areas']}\n")
                # prompt = prompt_template.format(expert_name=expert,time_frame=state['time_frame'])
                prompt = prompt_template.format(
                    expert_name=expert,
                    time_frame=state['time_frame'],
                    focus_areas=", ".join(state['focus_areas'])
                )

                try:
                    completion = self.llm.chat.completions.create(
                        model="gpt-4o-search-preview",
                        web_search_options={"search_context_size": "high"},
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                    )
                    logger.info(f"Web search OpenAI results: {completion}\n")
                    content = completion.choices[0].message.content
                    # annotations = completion.choices[0].message.get("annotations", [])
                    # annotations = completion.choices[0].message.annotations if hasattr(completion.choices[0].message, "annotations") else []
                    annotations = getattr(completion.choices[0].message, "annotations", [])

                    # Extract citations from annotations
                    citations = []
                    for ann in annotations:
                        if getattr(ann, "type", None) == "url_citation":
                            url_citation = getattr(ann, "url_citation", None)
                            if url_citation:
                                title = getattr(url_citation, "title", "")
                                url = getattr(url_citation, "url", "")
                                formatted_citation = f"{title} - {url}" if title else url
                                citations.append({
                                    "url": url,
                                    "title": title,
                                    "formatted": formatted_citation
                                })
                                
        
                    summary = {
                        "expert_name": expert,
                        "insights": content,
                        "citations": citations,
                        "timestamp": datetime.now().isoformat()
                    }

                    summaries.append(summary)
                    logger.info(f"Successfully processed expert: {expert} for focus_areas: {state['focus_areas']}: time_frame: {state['time_frame']}\n")

                except Exception as e:
                    logger.error(f"Error processing expert {expert}: {e}")

            state['summaries'] = summaries
            logger.info("Completed analysis for all experts.")
            return state

        def generate_final_analysis(state: GeneralExpertState) -> GeneralExpertState:
            utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(f"Generating final analysis report.\nTime: {utc_now}\n")
            output = ""
            output += "# GENERAL EXPERT ANALYSIS\n"
            output += "="*60 + "\n"
            output += f"**Report generated on:** {utc_now}\n\n"
            
            output += "## Time Frame\n"
            output += f"- {state['time_frame']}\n\n"
            
            output += "## Focus Areas\n"
            for area in state['focus_areas']:
                output += f"- {area}\n"
            output += "\n"
            
            output += "---\n\n"  # Horizontal line for separation

            for summary in state['summaries']:
                output += f"## {summary['expert_name']}\n"
                output += summary['insights'] + "\n\n"
                if summary['citations']:
                    output += "**Citations:**\n"
                    for cite in summary['citations']:
                        output += f"- {cite['formatted']}\n"
                    output += "\n"
            # Footer
            output += "="*60 + "\n"
            output += "End of General Expert Analysis Report\n"
            output += "="*60 + "\n"
            
                # if summary['citations']:
                #     output += "**Citations:**\n"
                #     for cite in summary['citations']:
                #         output += f"- {cite['title']}: {cite['url']}\n"
                #     output += "\n"

            state['final_output'] = output
            logger.info("Final analysis report generation complete.")
            return state

        workflow = StateGraph(GeneralExpertState)
        workflow.add_node("analyze", analyze_experts)
        workflow.add_node("finalize", generate_final_analysis)
        workflow.add_edge("analyze", "finalize")
        workflow.add_edge("finalize", END)
        workflow.set_entry_point("analyze")

        return workflow.compile()

    # async def run(self, expert_names: List[str], time_frame: str) -> str:
    async def run(self, expert_names: List[str], time_frame: str, focus_areas: List[str]) -> str:
        logger.info(f"\t X<----> Starting GeneralExpertAgent run. <---->X\n")
        agent = self.create_general_expert_agent()
        # initial_state = GeneralExpertState(
        #     expert_names=expert_names,
        #     summaries=[],
        #     time_frame=time_frame,
        #     final_output=""
        # )
        initial_state = GeneralExpertState(
                expert_names=expert_names,
                summaries=[],
                time_frame=time_frame,
                focus_areas=focus_areas,
                final_output=""
            )

        result = await agent.ainvoke(initial_state)
        logger.info(f"\t X<----> GeneralExpertAgent run complete. <---->X\n")
        return result['final_output']

# # # Example usage:
# # if __name__ == "__main__":
# #     agent = GeneralExpertAgent(openai_api_key="YOUR_OPENAI_KEY")
# #     output = asyncio.run(agent.run(["Elon Musk", "Sam Altman"]))
# #     print(output)
