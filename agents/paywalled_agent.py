##################################### ------ {Logs, LLM integrated - Live Agent} ------#####################################


import os
import asyncio
import logging
from typing import Dict, List, Any, TypedDict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, END

# Setup dedicated logger for this class
logger = logging.getLogger("paywalled_content_agent")
logger.setLevel(logging.INFO)

# Ensure no duplicate handlers if imported multiple times
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [PaywalledContentAgent] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class PaywalledContentState(TypedDict):
    content_sources: List[str]
    expert_tier: str
    summaries: List[Dict[str, Any]]
    final_output: str

class PaywalledContentAgent:
    def __init__(self, llm_api_key: str, username: str, password: str):
        logger.info(f"Initializing PaywalledContentAgent with DeepSeek Chat client.")
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            temperature=0.5,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=llm_api_key,
        )
        self.username = username
        self.password = password

    def scrape_content(self, source: str) -> str:
        """
        Placeholder function to scrape content from a paywalled source.
        Replace with actual scraping logic for specific websites.
        """
        logger.info(f"Scraping content from {source}")
        try:
            # Example: Login to a paywalled site and scrape content
            session = requests.Session()
            login_url = f"https://{source.lower().replace(' ', '')}.com/login"  # Placeholder URL
            login_data = {
                "username": self.username,
                "password": self.password
            }
            response = session.post(login_url, data=login_data)
            if response.status_code != 200:
                logger.error(f"Failed to log in to {source}: {response.status_code}")
                return f"Failed to log in to {source}"

            # Scrape content (example: fetch main article content)
            content_url = f"https://{source.lower().replace(' ', '')}.com/latest"  # Placeholder URL
            content_response = session.get(content_url)
            soup = BeautifulSoup(content_response.text, 'html.parser')
            # Example: Extract text from article body (adjust selector as needed)
            article_body = soup.find('div', class_='article-content') or soup.find('body')
            content = article_body.get_text(strip=True) if article_body else "No content found"
            logger.info(f"Successfully scraped content from {source}")
            return content[:5000]  # Limit content length to avoid LLM token limits
        except Exception as e:
            logger.error(f"Error scraping {source}: {str(e)}")
            return f"Error scraping {source}: {str(e)}"

    def create_paywalled_content_agent(self) -> StateGraph:
        def check_content_amount(state: PaywalledContentState) -> PaywalledContentState:
            logger.info(f"Checking content amount for {len(state['content_sources'])} sources.")
            return state

        def summarize_content(state: PaywalledContentState) -> PaywalledContentState:
            summaries = []
            bullet_count = 10 if state['expert_tier'] == 'tier1' else 5

            logger.info(f"Starting summarization for expert tier: {state['expert_tier']} ({bullet_count} bullets per source).")

            prompt_template = ChatPromptTemplate.from_template(
                """
                We are a family office sophisticated investor focused on geopolitics, macro, precious metals, 
                energy, commodities, crypto (especially bitcoin), and emerging technologies.
                
                Summarize the key insights relevant to us for investing in {bullet_count} short, insightful 
                informal narrative style, easy to read sentences (ideally each sentence should be not more than 10-15 words).
                
                Please start by giving the broader directional views and then any actionable insights after 
                and end with conclusions. Please end with any forecasts. The content should be for the last week 
                and be from comprehensive sources as possible.
                
                Please state the name of the expert and then the {bullet_count} bullets. Include no extra text or sections apart from that.
                
                Content: {content}
                """
            )

            for source in state['content_sources']:
                logger.info(f"Processing content source: {source}")
                # Scrape content from the source
                content = self.scrape_content(source)
                if "Error" in content or "Failed" in content:
                    summaries.append({
                        'source': source,
                        'expert_name': f"Expert from {source}",
                        'bullets': [f"Unable to summarize {source}: content retrieval failed"],
                        'timestamp': datetime.now().isoformat()
                    })
                    continue

                try:
                    # Call the LLM to summarize the content
                    prompt = prompt_template.format(bullet_count=bullet_count, content=content)
                    response = self.llm.invoke(prompt)
                    # Parse response (assuming LLM returns expert name followed by bullets)
                    response_lines = response.content.strip().split('\n')
                    expert_name = response_lines[0] if response_lines else f"Expert from {source}"
                    bullets = [line.strip('•- ') for line in response_lines[1:bullet_count+1] if line.strip().startswith(('•', '-'))]
                    # Ensure correct number of bullets
                    if len(bullets) < bullet_count:
                        bullets.extend([f"Additional insight {i+1} not available" for i in range(len(bullets), bullet_count)])
                    elif len(bullets) > bullet_count:
                        bullets = bullets[:bullet_count]

                    summary = {
                        'source': source,
                        'expert_name': expert_name,
                        'bullets': bullets,
                        'timestamp': datetime.now().isoformat()
                    }
                    summaries.append(summary)
                    logger.info(f"Completed summarization for source: {source}")
                except Exception as e:
                    logger.error(f"Error summarizing {source}: {str(e)}")
                    summaries.append({
                        'source': source,
                        'expert_name': f"Expert from {source}",
                        'bullets': [f"Error summarizing {source}: {str(e)}"],
                        'timestamp': datetime.now().isoformat()
                    })

            state['summaries'] = summaries
            logger.info("Summarization complete for all content sources.")
            return state

        def compile_output(state: PaywalledContentState) -> PaywalledContentState:
            logger.info("Compiling final output summary.")
            output = "PAYWALLED CONTENT SUMMARY\n" + "="*50 + "\n\n"

            for summary in state['summaries']:
                output += f"**{summary['expert_name']}**\n"
                for bullet in summary['bullets']:
                    output += f"• {bullet}\n"
                output += "\n"

            state['final_output'] = output
            logger.info("Final output summary compilation complete.")
            return state

        workflow = StateGraph(PaywalledContentState)
        workflow.add_node("check_content", check_content_amount)
        workflow.add_node("summarize", summarize_content)
        workflow.add_node("compile", compile_output)
        workflow.add_edge("check_content", "summarize")
        workflow.add_edge("summarize", "compile")
        workflow.add_edge("compile", END)
        workflow.set_entry_point("check_content")
        
        return workflow.compile()

    async def run(self, content_sources: List[str], expert_tier: str = "tier2") -> str:
        logger.info(f"\t X<----> Starting PaywalledContentAgent run. <---->X\n")
        agent = self.create_paywalled_content_agent()
        initial_state = PaywalledContentState(
            content_sources=content_sources,
            expert_tier=expert_tier,
            summaries=[],
            final_output=""
        )
        result = await agent.ainvoke(initial_state)
        logger.info(f"\t X<----> PaywalledContentAgent run complete. <---->X\n")
        return result['final_output']

# Example usage:
# if __name__ == "__main__":
#     agent = PaywalledContentAgent(
#         llm_api_key="YOUR_DEEPSEEK_API_KEY",
#         username="YOUR_USERNAME",
#         password="YOUR_PASSWORD"
#     )
#     output = asyncio.run(agent.run(["Financial Times", "Bloomberg"]))
#     print(output)