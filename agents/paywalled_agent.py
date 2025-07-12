# import os
# import asyncio
# import logging
# from typing import Dict, List, TypedDict
# from datetime import datetime
# from langchain.prompts import ChatPromptTemplate
# from openai import OpenAI, OpenAIError
# from pdfminer.high_level import extract_text
# from langgraph.graph import StateGraph, END
# from utils.paywall_pdf_utils import scrape_pdfs_from_paywalled_site
# from tenacity import retry, stop_after_attempt, wait_exponential

# # Setup logger
# logger = logging.getLogger("paywalled_content_agent")
# logger.setLevel(logging.INFO)
# if not logger.hasHandlers():
#     handler = logging.StreamHandler()
#     handler.setFormatter(logging.Formatter(
#         "%(asctime)s [PaywalledContentAgent] %(levelname)s: %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S"
#     ))
#     logger.addHandler(handler)

# class PaywalledContentState(TypedDict):
#     content_sources: List[str]
#     expert_tier: str
#     summaries: List[Dict[str, str | List[str] | str]]
#     final_output: str

# class PaywalledContentAgent:
#     def __init__(self, llm_api_key: str, username: str="ann", password: str="M3", login_url: str="htnter/", content_url: str="https-archive/", download_dir: str = "./inled_content/downloads", max_text_length: int = 10000):
#         logger.info("Initializing PaywalledContentAgent with OpenAI client.")
#         self.llm = OpenAI(api_key=llm_api_key)
#         self.username = username
#         self.password = password
#         self.login_url = login_url
#         self.content_url = content_url
#         self.download_dir = download_dir
#         self.max_text_length = max_text_length
#         os.makedirs(self.download_dir, exist_ok=True)

#     def get_latest_pdf_file(self) -> str | None:
#         pdfs = [f for f in os.listdir(self.download_dir) if f.endswith(".pdf")]
#         if not pdfs:
#             return None
#         return max((os.path.join(self.download_dir, f) for f in pdfs), key=os.path.getmtime)

#     def download_pdfs_from_source(self, content_url: str, max_pdfs: int = 3) -> List[str]:
#         logger.info(f"Downloading PDFs from source: {content_url}")
#         try:
#             downloaded_files = scrape_pdfs_from_paywalled_site(
#                 login_url=self.login_url,
#                 username=self.username,
#                 password=self.password,
#                 content_url=content_url,
#                 download_dir=self.download_dir,
#                 max_pdfs=max_pdfs,
#                 headless=False
#             )
#             logger.info(f"Downloaded files: {downloaded_files}")
#             return downloaded_files
#         except Exception as e:
#             logger.error(f"Error downloading PDFs from {content_url}: {e}")
#             raise

#     def download_latest_pdf(self) -> str | None:
#         logger.info("Downloading PDFs from paywalled site...")
#         try:
#             downloaded_files = self.download_pdfs_from_source(self.content_url, max_pdfs=3)
#             if not downloaded_files:
#                 logger.warning("No PDFs were downloaded.")
#                 return None
#             latest_pdf = self.get_latest_pdf_file()
#             logger.info(f"Latest downloaded PDF: {latest_pdf}")
#             return latest_pdf
#         except Exception as e:
#             logger.error(f"Failed to download or locate latest PDF: {str(e)}")
#             return None

#     def scrape_content(self, pdf_path: str | None) -> str:
#         logger.info(f"Scraping PDF content from: {pdf_path or 'latest downloaded file'}")
#         if not pdf_path:
#             pdf_path = self.download_latest_pdf()
#         if not pdf_path:
#             raise ValueError("No PDF available for summarization.")

#         try:
#             text = extract_text(pdf_path)
#             logger.info(f"PDF content extraction successful.\n{text[:500]}..")
#             return text[:self.max_text_length]
#         except Exception as e:
#             logger.error(f"Failed to extract text from PDF: {str(e)}")
#             raise ValueError(f"Failed to extract text from PDF: {str(e)}")

#     @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
#     def summarize_content(self, content: str, bullet_count: int) -> Dict[str, str | List[str]]:
#         prompt_template = ChatPromptTemplate.from_template(
#             """
#             We are a family office sophisticated investor focused on geopolitics, macro, precious metals, 
#             energy, commodities, crypto (especially bitcoin), and emerging technologies.

#             Summarize the key insights relevant to us for investing in {bullet_count} short, insightful 
#             informal narrative style, easy to read sentences (ideally each sentence not more than 10-15 words).

#             Start with broader directional views, then actionable insights, and end with conclusions or forecasts.

#             Provide the expert name followed by {bullet_count} bullet points only.

#             Content: {content}
#             """
#         )
#         try:
#             prompt = prompt_template.format(bullet_count=bullet_count, content=content)
#             response = self.llm.chat.completions.create(
#                 model="gpt-4",
#                 messages=[{"role": "user", "content": prompt}],
#                 temperature=0.5,
#                 max_tokens=1000
#             )
#             response_lines = response.choices[0].message.content.strip().split('\n')
#             expert_name = response_lines[0] if response_lines else "Unknown Expert"
#             bullets = [line.strip('•- ') for line in response_lines[1:] if line.strip().startswith(('•', '-'))]
#             if len(bullets) < bullet_count:
#                 bullets.extend([f"Additional insight {i+1} not available" for i in range(len(bullets), bullet_count)])
#             elif len(bullets) > bullet_count:
#                 bullets = bullets[:bullet_count]
#             return {
#                 'expert_name': expert_name,
#                 'bullets': bullets,
#                 'timestamp': datetime.now().isoformat()
#             }
#         except OpenAIError as e:
#             logger.error(f"Error summarizing content: {str(e)}")
#             raise

#     def create_paywalled_content_agent(self) -> StateGraph:
#         def summarize_content(state: PaywalledContentState) -> PaywalledContentState:
#             if not state['content_sources']:
#                 raise ValueError("No content sources provided.")
#             if state['expert_tier'] not in ['tier1', 'tier2']:
#                 raise ValueError(f"Invalid expert tier: {state['expert_tier']}")

#             summaries = []
#             bullet_count = 10 if state['expert_tier'] == 'tier1' else 5
#             run_timestamp = datetime.now().isoformat()

#             logger.info(f"Starting summarization for expert tier: {state['expert_tier']} ({bullet_count} bullets).")
#             for source in state['content_sources']:
#                 logger.info(f"Processing content source: {source}")
#                 try:
#                     content = self.scrape_content(pdf_path=source)
#                     summary = self.summarize_content(content, bullet_count)
#                     summary['source'] = source
#                     summary['timestamp'] = run_timestamp
#                     summaries.append(summary)
#                     logger.info(f"Completed summarization for source: {source}")
#                 except Exception as e:
#                     summaries.append({
#                         'source': source,
#                         'expert_name': f"Expert from {source}",
#                         'bullets': [f"Error summarizing {source}: {str(e)}"],
#                         'timestamp': run_timestamp
#                     })
#                     logger.error(f"Error summarizing {source}: {str(e)}")
#             state['summaries'] = summaries
#             logger.info("Summarization complete for all content sources.")
#             return state

#         def compile_output(state: PaywalledContentState) -> PaywalledContentState:
#             logger.info("Compiling final output summary.")
#             output = "PAYWALLED CONTENT SUMMARY\n" + "=" * 50 + "\n\n"
#             for summary in state['summaries']:
#                 output += f"**{summary['expert_name']}**\n"
#                 for bullet in summary['bullets']:
#                     output += f"• {bullet}\n"
#                 output += "\n"
#             state['final_output'] = output
#             logger.info("Final output summary compilation complete.")
#             return state

#         workflow = StateGraph(PaywalledContentState)
#         workflow.add_node("summarize", summarize_content)
#         workflow.add_node("compile", compile_output)
#         workflow.add_edge("summarize", "compile")
#         workflow.add_edge("compile", END)
#         workflow.set_entry_point("summarize")
#         return workflow.compile()

#     async def run(self, content_sources: List[str], expert_tier: str = "tier2") -> str:
#         logger.info("\t X<----> Starting PaywalledContentAgent run. <---->X\n")
#         agent = self.create_paywalled_content_agent()
#         initial_state = PaywalledContentState(
#             content_sources=content_sources,
#             expert_tier=expert_tier,
#             summaries=[],
#             final_output=""
#         )
#         result = await agent.ainvoke(initial_state)
#         logger.info("\t X<----> PaywalledContentAgent run complete. <---->X\n")
#         return result['final_output']


## Version 3
import os
import asyncio
import logging
from typing import Dict, List, TypedDict
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from openai import OpenAI, OpenAIError
from pdfminer.high_level import extract_text
from langgraph.graph import StateGraph, END
from utils.paywall_pdf_utils import scrape_pdfs_from_paywalled_site
from tenacity import retry, stop_after_attempt, wait_exponential
import base64
from pathlib import Path

# Setup logger
logger = logging.getLogger("paywalled_content_agent")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [PaywalledContentAgent] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)

class PaywalledContentState(TypedDict):
    content_sources: List[str]
    expert_tier: str
    summaries: List[Dict[str, str | List[str] | str]]
    final_output: str

class PaywalledContentAgent:
        logger.info("Initializing PaywalledContentAgent with OpenAI client.")
        self.llm = OpenAI(api_key=llm_api_key)
        self.username = username
        self.password = password
        self.login_url = login_url
        self.content_url = content_url
        self.download_dir = download_dir
        self.max_text_length = max_text_length
        os.makedirs(self.download_dir, exist_ok=True)

    def get_latest_pdf_file(self) -> str | None:
        """Get the most recently modified PDF file"""
        try:
            pdfs = [f for f in os.listdir(self.download_dir) if f.endswith(".pdf")]
            if not pdfs:
                logger.warning("No PDF files found in download directory")
                return None
            latest_pdf = max((os.path.join(self.download_dir, f) for f in pdfs), key=os.path.getmtime)
            logger.info(f"Latest PDF found: {latest_pdf}")
            return latest_pdf
        except Exception as e:
            logger.error(f"Error finding latest PDF: {e}")
            return None

    def download_pdfs_from_source(self, content_url: str, max_pdfs: int = 3) -> List[str]:
        """Download PDFs from source - synchronous method"""
        logger.info(f"Downloading PDFs from source: {content_url}")
        try:
            downloaded_files = scrape_pdfs_from_paywalled_site(
                login_url=self.login_url,
                username=self.username,
                password=self.password,
                content_url=content_url,
                download_dir=self.download_dir,
                max_pdfs=max_pdfs,
                headless=False
            )
            logger.info(f"Downloaded files: {downloaded_files}")
            return downloaded_files
        except Exception as e:
            logger.error(f"Error downloading PDFs from {content_url}: {e}")
            raise

    def download_latest_pdf(self) -> str | None:
        """Download latest PDF and return its path"""
        logger.info("Downloading PDFs from paywalled site...")
        try:
            downloaded_files = self.download_pdfs_from_source(self.content_url, max_pdfs=3)
            if not downloaded_files:
                logger.warning("No PDFs were downloaded.")
                return None
            latest_pdf = self.get_latest_pdf_file()
            logger.info(f"Latest downloaded PDF: {latest_pdf}")
            return latest_pdf
        except Exception as e:
            logger.error(f"Failed to download or locate latest PDF: {str(e)}")
            return None

    def validate_pdf_path(self, pdf_path: str) -> bool:
        """Validate that PDF path exists and is readable"""
        if not pdf_path:
            return False
        
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF path does not exist: {pdf_path}")
            return False
        
        if not path.is_file():
            logger.error(f"PDF path is not a file: {pdf_path}")
            return False
        
        if path.suffix.lower() != '.pdf':
            logger.error(f"File is not a PDF: {pdf_path}")
            return False
        
        return True

    def encode_pdf_to_base64(self, pdf_path: str) -> str:
        """Encode PDF to base64 for direct API submission"""
        try:
            with open(pdf_path, "rb") as pdf_file:
                return base64.b64encode(pdf_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding PDF to base64: {e}")
            raise

    def scrape_content(self, pdf_path: str | None) -> str:
        """Extract content from PDF with improved error handling"""
        logger.info(f"Scraping PDF content from: {pdf_path or 'latest downloaded file'}")
        
        # Handle case where no PDF path is provided
        if not pdf_path:
            logger.info("No PDF path provided, attempting to download latest PDF")
            pdf_path = self.download_latest_pdf()
        
        if not pdf_path:
            raise ValueError("No PDF available for summarization.")
        
        # Validate PDF path
        if not self.validate_pdf_path(pdf_path):
            raise ValueError(f"Invalid PDF path: {pdf_path}")

        try:
            logger.info(f"Attempting to extract text from: {pdf_path}")
            text = extract_text(pdf_path)
            
            if not text or len(text.strip()) < 10:
                logger.warning(f"Very little text extracted from PDF: {len(text) if text else 0} characters")
                raise ValueError("PDF appears to be empty or contains mostly non-text content")
            
            logger.info(f"PDF content extraction successful. Extracted {len(text)} characters")
            logger.info(f"First 500 characters: {text[:500]}")
            
            return text[:self.max_text_length]
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def summarize_content(self, content: str, bullet_count: int) -> Dict[str, str | List[str]]:
        """Summarize content with improved error handling"""
        logger.info(f"Starting summarization with {len(content)} characters, {bullet_count} bullets")
        
        if not content or len(content.strip()) < 10:
            raise ValueError("Content is empty or too short to summarize")
        
        prompt_template = ChatPromptTemplate.from_template(
            """
            We are a family office sophisticated investor focused on geopolitics, macro, precious metals, 
            energy, commodities, crypto (especially bitcoin), and emerging technologies.

            Summarize the key insights relevant to us for investing in {bullet_count} short, insightful 
            informal narrative style, easy to read sentences (ideally each sentence not more than 10-15 words).

            Start with broader directional views, then actionable insights, and end with conclusions or forecasts.

            Provide the expert name followed by {bullet_count} bullet points only.

            Content: {content}
            """
        )
        
        try:
            prompt = prompt_template.format(bullet_count=bullet_count, content=content)
            logger.info(f"Sending prompt to OpenAI API (length: {len(prompt)})")
            
            response = self.llm.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content.strip()
            logger.info(f"Received response from OpenAI: {response_content[:200]}...")
            
            response_lines = response_content.split('\n')
            expert_name = response_lines[0] if response_lines else "Unknown Expert"
            bullets = [line.strip('•- ') for line in response_lines[1:] if line.strip().startswith(('•', '-'))]
            
            # Handle case where bullets weren't formatted correctly
            if len(bullets) < bullet_count:
                # Try to split the response differently
                all_lines = [line.strip() for line in response_lines[1:] if line.strip()]
                if len(all_lines) >= bullet_count:
                    bullets = all_lines[:bullet_count]
                else:
                    bullets.extend([f"Additional insight {i+1} not available" for i in range(len(bullets), bullet_count)])
            elif len(bullets) > bullet_count:
                bullets = bullets[:bullet_count]
            
            result = {
                'expert_name': expert_name,
                'bullets': bullets,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Summarization complete. Expert: {expert_name}, Bullets: {len(bullets)}")
            return result
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error during summarization: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
    def summarize_pdf_directly(self, pdf_path: str, bullet_count: int) -> Dict[str, str | List[str]]:
        """Alternative method: Send PDF directly to OpenAI for analysis"""
        logger.info(f"Attempting direct PDF summarization: {pdf_path}")
        
        if not self.validate_pdf_path(pdf_path):
            raise ValueError(f"Invalid PDF path: {pdf_path}")
        
        try:
            # Note: This is a placeholder for future implementation
            # OpenAI's vision API doesn't support PDF yet, but this structure
            # is ready for when it does or for other multimodal APIs
            pdf_base64 = self.encode_pdf_to_base64(pdf_path)
            
            prompt = f"""
            We are a family office sophisticated investor focused on geopolitics, macro, precious metals, 
            energy, commodities, crypto (especially bitcoin), and emerging technologies.

            Analyze this PDF document and provide {bullet_count} key investment insights in short, 
            informal narrative style sentences (10-15 words each).

            Start with broader directional views, then actionable insights, and end with conclusions or forecasts.
            
            Provide the expert name followed by {bullet_count} bullet points only.
            """
            
            # For now, fall back to text extraction
            logger.info("Direct PDF analysis not yet supported, falling back to text extraction")
            content = extract_text(pdf_path)
            return self.summarize_content(content, bullet_count)
            
        except Exception as e:
            logger.error(f"Error in direct PDF summarization: {str(e)}")
            raise

    def create_paywalled_content_agent(self) -> StateGraph:
        def summarize_content_node(state: PaywalledContentState) -> PaywalledContentState:
            if not state['content_sources']:
                raise ValueError("No content sources provided.")
            if state['expert_tier'] not in ['tier1', 'tier2']:
                raise ValueError(f"Invalid expert tier: {state['expert_tier']}")

            summaries = []
            bullet_count = 10 if state['expert_tier'] == 'tier1' else 5
            run_timestamp = datetime.now().isoformat()

            logger.info(f"Starting summarization for expert tier: {state['expert_tier']} ({bullet_count} bullets).")
            
            for i, source in enumerate(state['content_sources']):
                logger.info(f"Processing content source {i+1}/{len(state['content_sources'])}: {source}")
                try:
                    # Validate source path
                    if not self.validate_pdf_path(source):
                        raise ValueError(f"Invalid PDF source: {source}")
                    
                    # Try text extraction first
                    content = self.scrape_content(pdf_path=source)
                    summary = self.summarize_content(content, bullet_count)
                    summary['source'] = source
                    summary['timestamp'] = run_timestamp
                    summaries.append(summary)
                    logger.info(f"Completed summarization for source: {source}")
                    
                except Exception as e:
                    logger.error(f"Error summarizing {source}: {str(e)}")
                    # Try direct PDF method as fallback
                    try:
                        logger.info(f"Attempting direct PDF summarization for {source}")
                        summary = self.summarize_pdf_directly(source, bullet_count)
                        summary['source'] = source
                        summary['timestamp'] = run_timestamp
                        summaries.append(summary)
                        logger.info(f"Direct PDF summarization successful for: {source}")
                    except Exception as e2:
                        logger.error(f"Direct PDF summarization also failed for {source}: {str(e2)}")
                        summaries.append({
                            'source': source,
                            'expert_name': f"Expert from {Path(source).name}",
                            'bullets': [f"Error summarizing {Path(source).name}: {str(e)}"],
                            'timestamp': run_timestamp
                        })
            
            if not summaries:
                raise ValueError("No content could be summarized from any source")
            
            state['summaries'] = summaries
            logger.info(f"Summarization complete for {len(summaries)} sources.")
            return state

        def compile_output(state: PaywalledContentState) -> PaywalledContentState:
            logger.info("Compiling final output summary.")
            output = "PAYWALLED CONTENT SUMMARY\n" + "=" * 50 + "\n\n"
            
            for summary in state['summaries']:
                output += f"**{summary['expert_name']}**\n"
                output += f"Source: {Path(summary['source']).name}\n"
                output += f"Timestamp: {summary['timestamp']}\n\n"
                
                for bullet in summary['bullets']:
                    output += f"• {bullet}\n"
                output += "\n" + "-" * 30 + "\n\n"
            
            state['final_output'] = output
            logger.info("Final output summary compilation complete.")
            return state

        workflow = StateGraph(PaywalledContentState)
        workflow.add_node("summarize", summarize_content_node)
        workflow.add_node("compile", compile_output)
        workflow.add_edge("summarize", "compile")
        workflow.add_edge("compile", END)
        workflow.set_entry_point("summarize")
        return workflow.compile()

    async def run(self, content_sources: List[str], expert_tier: str = "tier2") -> str:
        """Run the paywalled content agent"""
        logger.info(f"\t X<----> Starting PaywalledContentAgent run with {len(content_sources)} sources <---->X\n")
        
        # Validate inputs
        if not content_sources:
            raise ValueError("No content sources provided")
        
        # Validate all PDF paths before processing
        valid_sources = []
        for source in content_sources:
            if self.validate_pdf_path(source):
                valid_sources.append(source)
                logger.info(f"Valid source: {source}")
            else:
                logger.warning(f"Invalid source skipped: {source}")
        
        if not valid_sources:
            raise ValueError("No valid PDF sources found")
        
        agent = self.create_paywalled_content_agent()
        initial_state = PaywalledContentState(
            content_sources=valid_sources,
            expert_tier=expert_tier,
            summaries=[],
            final_output=""
        )
        
        try:
            result = await agent.ainvoke(initial_state)
            logger.info("\t X<----> PaywalledContentAgent run complete. <---->X\n")
            return result['final_output']
        except Exception as e:
            logger.error(f"Error during agent execution: {str(e)}")
            raise