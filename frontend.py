##################################### ------ {Web search Integrated - Live Agent} ------#####################################
import streamlit as st
import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any
import time
import logging
from agents.paywalled_agent import PaywalledContentAgent
from agents.general_expert_agent import GeneralExpertAgent
from agents.podcast_agent import PodcastAgent
from utils.save_files_utils import save_document_all_formats

from pathlib import Path
import streamlit as st

import os
import mimetypes
import pandas as pd
from datetime import datetime


# Configure logging for this module specifically
def setup_logging(base_dir: Path):
    """Setup isolated logging for the main app"""
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a unique logger for this module
    logger = logging.getLogger('investment_research_app')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid parent logger interference
    logger.propagate = False
    
    return logger

class InvestmentResearchAgents:
    def __init__(
        self, 
        deepseek_api_key: str = None,
        anthropic_api_key: str = None,
        gemini_api_key: str = None,
        openai_api_key: str = None,
        base_dir: Path = None
    ):
        self.deepseek_api_key = deepseek_api_key
        self.anthropic_api_key = anthropic_api_key
        self.gemini_api_key = gemini_api_key
        self.openai_api_key = openai_api_key
        self.base_dir = base_dir
        self.logger = setup_logging(base_dir)
        
        # Select primary API key (first available)
        self.primary_api_key = next(
            (key for key in [deepseek_api_key, anthropic_api_key, gemini_api_key, openai_api_key] if key),
            None
        )
        self.logger.info(f"Using {self.primary_api_key} as primary api key")
        
        if not self.primary_api_key:
            raise ValueError("At least one API key must be provided to initialize agents.")
        
        try:
            self.paywalled_agent = PaywalledContentAgent(
                self.primary_api_key,  
                # username="",
                # password=""
            )
            self.general_expert_agent = GeneralExpertAgent(self.primary_api_key)
            self.podcast_agent = PodcastAgent(self.primary_api_key)
            self.logger.info("All agents initialized successfully with primary API key\n")
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {str(e)}")
            raise
        
        self.tsi_model = """
        TSI Model: 3-circle Venn diagram with geopolitics (multipolar world with conflict), 
        macro (high debt leading to money printing and inflation), and AI+tech (deflation/depression).
        """

    def run_paywalled_agent(self, content_sources: List[str], expert_tier: str = "tier2"):
        """Run paywalled content agent with error handling - SYNCHRONOUS"""
        try:
            self.logger.info(f"[Main]>> Starting paywalled agent with {len(content_sources)} sources, tier: {expert_tier}. <<[Main]\n")
            
            # Validate content sources
            if not content_sources:
                raise ValueError("No content sources provided")
            
            # Log each source for debugging
            for i, source in enumerate(content_sources):
                self.logger.info(f"[Main]>> Source {i+1}: {source}")
                if not os.path.exists(source):
                    self.logger.warning(f"[Main]>> Source file does not exist: {source}")
            
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the agent
            result = loop.run_until_complete(self.paywalled_agent.run(content_sources, expert_tier))
            
            self.logger.info(f"[Main]>> Paywalled agent completed successfully. <<[Main]\n")
            return result
            
        except Exception as e:
            self.logger.error(f"X** [Main]>> Paywalled agent failed: {str(e)}. <<[Main]\n")
            raise

    def download_pdfs_from_source(self, content_url: str, max_pdfs: int = 3):
        """Download PDFs from source - SYNCHRONOUS"""
        try:
            self.logger.info(f"[Main]>> Starting PDF download from: {content_url}")
            
            # Call the synchronous method directly
            downloaded_paths = self.paywalled_agent.download_pdfs_from_source(content_url, max_pdfs)
            
            self.logger.info(f"[Main]>> Download completed. Files: {downloaded_paths}")
            return downloaded_paths
            
        except Exception as e:
            self.logger.error(f"X** [Main]>> PDF download failed: {str(e)}")
            raise

    # Alternative async versions if you prefer to keep async structure
    async def run_paywalled_agent_async(self, content_sources: List[str], expert_tier: str = "tier2"):
        """Run paywalled content agent with error handling - ASYNC"""
        try:
            self.logger.info(f"[Main]>> Starting paywalled agent with {len(content_sources)} sources, tier: {expert_tier}. <<[Main]\n")
            
            # Validate content sources
            if not content_sources:
                raise ValueError("No content sources provided")
            
            # Log each source for debugging
            for i, source in enumerate(content_sources):
                self.logger.info(f"[Main]>> Source {i+1}: {source}")
                if not os.path.exists(source):
                    self.logger.warning(f"[Main]>> Source file does not exist: {source}")
            
            result = await self.paywalled_agent.run(content_sources, expert_tier)
            
            self.logger.info(f"[Main]>> Paywalled agent completed successfully. <<[Main]\n")
            return result
            
        except Exception as e:
            self.logger.error(f"X** [Main]>> Paywalled agent failed: {str(e)}. <<[Main]\n")
            raise

    async def download_pdfs_from_source_async(self, content_url: str, max_pdfs: int = 3):
        """Download PDFs from source - ASYNC wrapper"""
        try:
            self.logger.info(f"[Main]>> Starting PDF download from: {content_url}")
            
            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            downloaded_paths = await loop.run_in_executor(
                None, 
                self.paywalled_agent.download_pdfs_from_source, 
                content_url, 
                max_pdfs
            )
            
            self.logger.info(f"[Main]>> Download completed. Files: {downloaded_paths}")
            return downloaded_paths
            
        except Exception as e:
            self.logger.error(f"X** [Main]>> PDF download failed: {str(e)}")
            raise


    # async def run_general_expert_agent(self, expert_names: List[str]):
    async def run_general_expert_agent(self, expert_names: List[str], time_frame: str, focus_areas: List[str]):
        """Run general expert agent with error handling"""
        try:
            self.logger.info(f"[Main]>> Starting general expert agent with {len(expert_names)} experts. <<[Main]\n")
            # result = await self.general_expert_agent.run(expert_names)
            result = await self.general_expert_agent.run(
                    expert_names=expert_names,
                    time_frame=time_frame,
                    focus_areas=focus_areas
                )
            self.logger.info(f"[Main]>> General expert agent completed successfully. <<[Main]\n")
            return result
        except Exception as e:
            self.logger.error(f"X** [Main]>> General expert agent failed: {str(e)}. <<[Main]\n")
            raise

    ## Changed 
    async def run_podcast_agent(self, podcast_links: List[str]):
        """Run podcast agent with error handling"""
        try:
            self.logger.info(f"[Main]>> Starting podcast agent for provided links. <<[Main]\n")
            result = await self.podcast_agent.run(podcast_links)
            self.logger.info(f"[Main]>> Podcast agent completed successfully. <<[Main]\n")
            return result
        except Exception as e:
            self.logger.error(f"X** [Main]>> Podcast agent failed: {str(e)}. <<[Main]\n")
            raise



def setup_directories():
    """Setup required directories"""
    base_dir = Path("investment_research_outputs")
    dirs = ["paywalled_content", "general_experts", "podcast_analysis", "combined_analysis", "logs"]
    for directory in dirs:
        (base_dir / directory).mkdir(parents=True, exist_ok=True)
    return base_dir

def save_document(content: str, filename: str, folder: str, base_dir: Path):
    """Save document with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{timestamp}_{filename}"
    file_path = base_dir / folder / full_filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(file_path)

def log_activity(message: str, base_dir: Path):
    """Log activity to daily log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    log_file = base_dir / "logs" / f"activity_{datetime.now().strftime('%Y%m%d')}.log"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def reset_processing_state():
    """Reset all processing states"""
    st.session_state.processing_paywalled = False
    st.session_state.processing_general = False
    st.session_state.processing_podcast = False
    st.session_state.processing_suite = False

def main():
    st.set_page_config(
        page_title="Investment Research AI Agents",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    if 'base_dir' not in st.session_state:
        st.session_state.base_dir = setup_directories()

    if 'agents' not in st.session_state:
        st.session_state.agents = None
    
    # Initialize individual processing states
    if 'processing_paywalled' not in st.session_state:
        st.session_state.processing_paywalled = False
    if 'processing_general' not in st.session_state:
        st.session_state.processing_general = False
    if 'processing_podcast' not in st.session_state:
        st.session_state.processing_podcast = False
    if 'processing_suite' not in st.session_state:
        st.session_state.processing_suite = False

    st.title("🚀 Investment Research AI Agents")
    st.markdown("**Sophisticated AI-powered analysis for family office investment decisions**")

    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("API Keys")
        
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            type="password",
            help="Enter your DeepSeek API key to enable DeepSeek agent"
        )
        
        anthropic_key = st.text_input(
            "Anthropic Claude API Key",
            type="password",
            help="Enter your Anthropic Claude API key"
        )
        
        gemini_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key"
        )
        
        openai_key = st.text_input(
            "OpenAI ChatGPT API Key",
            type="password",
            help="Enter your OpenAI ChatGPT API key"
        )
        
        # Check if at least one API key is provided
        if any([deepseek_key, anthropic_key, gemini_key, openai_key]):
            if st.session_state.agents is None:
                try:
                    # Initialize agents with available keys
                    st.session_state.agents = InvestmentResearchAgents(
                        deepseek_api_key=deepseek_key,
                        anthropic_api_key=anthropic_key,
                        gemini_api_key=gemini_key,
                        openai_api_key=openai_key,
                        base_dir=st.session_state.base_dir
                    )
                    st.success("✅ Agents initialized!")
                except Exception as e:
                    st.error(f"❌ Failed to initialize agents: {str(e)}. Please check your API key.")
        else:
            st.warning("⚠️ Please enter at least one API key to continue")
            st.stop()
        
        st.divider()
        
        # Processing status
        st.subheader("🔄 Processing Status")
        if st.session_state.processing_paywalled:
            st.warning("🔄 Paywalled Agent Running...")
        elif st.session_state.processing_general:
            st.warning("🔄 General Expert Agent Running...")
        elif st.session_state.processing_podcast:
            st.warning("🔄 Podcast Agent Running...")
        elif st.session_state.processing_suite:
            st.warning("🔄 Complete Suite Running...")
        else:
            st.success("✅ All Agents Ready")
        
        # Reset button
        if st.button("🔄 Reset All Processing States"):
            reset_processing_state()
            st.rerun()
        
        st.divider()
        
        with st.expander("📊 TSI Model Reference"):
            st.markdown("""
            **TSI Framework Components:**
            1. Wealth Inequality
            2. Debt Stress  
            3. Tech Disruption
            4. Resource Concentration
            5. Currency Instability
            6. Geopolitical Tension
            
            *3-circle Venn: Geopolitics × Macro × AI/Tech*
            """)
    
  
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📰 Paywalled Content", 
        "👥 General Experts", 
        "🎙️ Podcast Analysis", 
        "📋 Combined Dashboard",
        "📁 File Manager"
    ])



    ## Version 3
    # Fixed Streamlit frontend code
    # Tab 1: Paywalled Content
    with tab1:
        st.header("📰 Paywalled Content Analysis")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Step 1: Choose Expert or Custom URL")
            expert_tier = st.selectbox(
                "Select Expert Tier",
                ["tier1", "tier2"],
                help="Tier 1: 10 bullets (Jim Rickards, Luke Gromen, etc.) | Tier 2: 5 bullets",
                key="paywalled_tier"
            )

            tier1_experts = {
                "Chris Macintosh": "https://capexinsider.com/login/insider-weekly-archive/",
                "Luke Gromen": "",
                "Tom Luongo": "",
                "Doomberg": ""
            }

            tier2_experts = {
                "Expert A": "",
                "Expert B": "",
                "Expert C": "",
                "Expert D": ""
            }

            expert_dict = tier1_experts if expert_tier == "tier1" else tier2_experts
            selected_expert = st.selectbox(
                "Select Expert or Source",
                list(expert_dict.keys()) + ["Custom..."],
                key="paywalled_selected_expert"
            )

            if selected_expert == "Custom...":
                custom_url = st.text_input("Enter custom content URL:", key="paywalled_custom_url")
            else:
                custom_url = expert_dict[selected_expert]

            st.write(f"🔗 Content URL to be scraped: `{custom_url}`")

        with col2:
            st.subheader("Step 2: Scrape & Download PDFs")
            scrape_button = st.button("📥 Scrape & Download Top PDFs", key="btn_scrape_pdf", disabled=st.session_state.processing_paywalled)

            if scrape_button and custom_url:
                st.session_state.processing_paywalled = True
                try:
                    with st.spinner("Downloading PDFs..."):
                        # Use synchronous method instead of asyncio.run
                        downloaded_paths = st.session_state.agents.download_pdfs_from_source(custom_url)
                        if not downloaded_paths:
                            st.warning("⚠️ No PDFs were downloaded. Check the URL or try again.")
                        else:
                            st.success(f"✅ Downloaded {len(downloaded_paths)} PDFs.")
                            st.session_state["available_paywalled_pdfs"] = downloaded_paths
                            log_activity(f"Downloaded PDFs from {custom_url}: {downloaded_paths}", st.session_state.base_dir)
                            
                            # Show downloaded files
                            st.info("📄 Downloaded files:")
                            for path in downloaded_paths:
                                st.write(f"• {os.path.basename(path)}")
                                
                except Exception as e:
                    st.error(f"❌ Failed to download PDFs: {str(e)}")
                    log_activity(f"Error downloading PDFs from {custom_url}: {str(e)}", st.session_state.base_dir)
                    st.exception(e)  # Show full traceback for debugging
                finally:
                    st.session_state.processing_paywalled = False
                    st.rerun()

        st.divider()

        st.subheader("Step 3: Select a PDF & Run Summary")
        # Step 3: Select a PDF & Run Summary
        pdf_dir = Path("./investment_research_outputs/paywalled_content/downloads").resolve()
        
        # Ensure directory exists
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Get available PDFs
        available_pdfs = sorted(pdf_dir.glob("*.pdf"), key=os.path.getmtime, reverse=True)

        if available_pdfs:
            pdf_options = {p.name: str(p) for p in available_pdfs}
            selected_pdf_name = st.selectbox(
                "📄 Choose a downloaded PDF to summarize",
                list(pdf_options.keys()),
                key="paywalled_selected_pdf"
            )
            selected_pdf = pdf_options[selected_pdf_name]
            
            # Show PDF details
            pdf_path = Path(selected_pdf)
            if pdf_path.exists():
                file_size = pdf_path.stat().st_size
                mod_time = datetime.fromtimestamp(pdf_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                st.info(f"📊 Selected PDF: {pdf_path.name} | Size: {file_size:,} bytes | Modified: {mod_time}")
            else:
                st.error(f"❌ Selected PDF does not exist: {selected_pdf}")

            run_summary = st.button("🚀 Run Paywalled Summary Agent", key="btn_run_summary", disabled=st.session_state.processing_paywalled)

            if run_summary and selected_pdf:
                st.session_state.processing_paywalled = True
                try:
                    with st.spinner(f"Summarizing {selected_pdf_name}..."):
                        # Add debugging information
                        st.info(f"🔍 Processing PDF: {selected_pdf}")
                        st.info(f"📊 Expert Tier: {expert_tier}")
                        
                        # Validate PDF before processing
                        if not os.path.exists(selected_pdf):
                            raise FileNotFoundError(f"PDF file not found: {selected_pdf}")
                        
                        # Use synchronous method instead of asyncio.run
                        result = st.session_state.agents.run_paywalled_agent(
                            content_sources=[selected_pdf],
                            expert_tier=expert_tier
                        )
                        
                        if not result or len(result.strip()) < 10:
                            st.warning("⚠️ Summary appears to be empty or too short. Check the PDF content.")
                        else:
                            filename = f"paywalled_summary_{Path(selected_pdf).stem}.txt"
                            saved_paths = save_document_all_formats(
                                result,
                                filename,
                                "paywalled_content",
                                st.session_state.base_dir
                            )
                            st.success(f"✅ Summary complete for {selected_pdf_name}.")
                            log_activity(f"Summary created for {selected_pdf}, saved to {saved_paths}", st.session_state.base_dir)
                            
                            # Show preview of result
                            st.subheader("📝 Summary Preview")
                            st.text_area("Generated Summary", result[:500] + "..." if len(result) > 500 else result, height=200)
                            
                except ValueError as e:
                    st.error(f"❌ Summary failed: {str(e)}")
                    log_activity(f"Error during summary for {selected_pdf}: {str(e)}", st.session_state.base_dir)
                except Exception as e:
                    st.error(f"❌ Unexpected error during summary: {str(e)}")
                    log_activity(f"Unexpected error during summary for {selected_pdf}: {str(e)}", st.session_state.base_dir)
                    st.exception(e)  # Show full traceback for debugging
                finally:
                    st.session_state.processing_paywalled = False
                    st.rerun()
        else:
            st.info("📭 No PDFs available yet. Please scrape them first.")
            # Show what's in the directory for debugging
            st.write(f"📁 Looking in directory: {pdf_dir}")
            if pdf_dir.exists():
                all_files = list(pdf_dir.glob("*"))
                if all_files:
                    st.write("📄 Files found in directory:")
                    for file in all_files:
                        st.write(f"• {file.name} ({'PDF' if file.suffix.lower() == '.pdf' else 'Other'})")
                else:
                    st.write("📭 Directory is empty")
            else:
                st.write("❌ Directory does not exist")

        st.divider()
        # st.subheader("📈 Expert Insights Preview")

        output_dir = st.session_state.base_dir / "paywalled_content"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        
        # Results section
        st.subheader("📈 Paywalled Expert Insights Preview")

        paywalled_dir = st.session_state.base_dir / "paywalled_content"
        paywalled_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(paywalled_dir.glob("*.txt"), key=os.path.getmtime, reverse=True)

        if files:
            latest_file = files[0]
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            preview = content[:500] + "..." if len(content) > 500 else content
            st.text_area("Preview", preview, height=200, key="paywalled_preview")

            if st.button("📄 View Full Analysis", key="paywalled_view"):
                st.text_area("Full Summary", content, height=400, key="paywalled_full")
        else:
            st.info("📭 No summaries available yet. Process a PDF first to see insights here.")
            
        # Debug information (can be removed in production)
        if st.checkbox("🔧 Show Debug Information", key="debug_paywalled"):
            st.subheader("Debug Information")
            st.write(f"📁 PDF Directory: {pdf_dir}")
            st.write(f"📁 Output Directory: {output_dir}")
            st.write(f"📊 Processing State: {st.session_state.processing_paywalled}")
            
            if 'available_paywalled_pdfs' in st.session_state:
                st.write(f"📄 Available PDFs in session: {st.session_state.available_paywalled_pdfs}")
                
            # Show recent log entries if available
            try:
                log_file = st.session_state.base_dir / "activity.log"
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        recent_lines = lines[-10:]  # Last 10 lines
                        st.text_area("Recent Log Entries", "".join(recent_lines), height=150)
            except Exception as e:
                st.write(f"Could not read log file: {e}")
                
    # Tab 2: General Experts
    with tab2:
        st.header("👥 General Expert Analysis")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Expert Selection")
            default_experts = [
                "Bob Moriarty",
                "Kitco News", 
                "Mike Maloney",
                "Peter Schiff",
                "Silver Institute"
            ]
            
            selected_experts = st.multiselect(
                "Select Experts to Analyze",
                options=default_experts + ["Custom..."],
                default=default_experts[:3],
                key="general_experts"
            )
            
            if "Custom..." in selected_experts:
                custom_experts = st.text_area(
                    "Enter custom experts (one per line)",
                    height=100,
                    key="general_custom_experts"
                )
                if custom_experts:
                    custom_list = [s.strip() for s in custom_experts.split('\n') if s.strip()]
                    selected_experts = [s for s in selected_experts if s != "Custom..."] + custom_list
        
        with col2:
            st.subheader("Analysis Settings")
            time_window = st.selectbox(
                "Time Window",
                ["Last 7 days", "Last 14 days", "Last 30 days"],
                index=0,
                key="general_time_window"
            )
            
            focus_areas = st.multiselect(
                "Focus Areas",
                ["Precious Metals", "Crypto", "Macro Economics", "Geopolitics", "Energy"],
                default=["Precious Metals", "Macro Economics"],
                key="general_focus_areas"
            )
            
            # Status indicator
            if st.session_state.processing_general:
                st.error("🔄 Processing...")
            else:
                st.success("✅ Ready")
            
            # Run button
            run_general = st.button(
                "🚀 Run Expert Analysis",
                disabled=st.session_state.processing_general or not selected_experts or any([
                    st.session_state.processing_paywalled,
                    st.session_state.processing_podcast,
                    st.session_state.processing_suite
                ]),
                use_container_width=True,
                key="btn_general"
            )
            
            # Process general expert analysis
            if run_general and selected_experts:
                st.session_state.processing_general = True
                try:
                    with st.spinner("Analyzing expert insights..."):
                        log_activity(f"Started general expert analysis for {len(selected_experts)} experts", st.session_state.base_dir)
                        
                        # Run the agent
                        result = asyncio.run(st.session_state.agents.run_general_expert_agent(
                            # expert_names=selected_experts
                            expert_names=selected_experts,
                            time_frame=time_window,
                            focus_areas=focus_areas
                        ))
                        
                        # # Save result
                        # filename = "general_experts_analysis.txt"
                        # saved_path = save_document(
                        #     result, 
                        #     filename, 
                        #     "general_experts", 
                        #     st.session_state.base_dir
                        # )
                        ## Updated save results
                        # Save result in txt, md, pdf
                        # filename = "general_experts_analysis.txt"
                        filename = f"general_experts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        saved_paths = save_document_all_formats(
                            result, 
                            filename, 
                            "general_experts", 
                            st.session_state.base_dir
                        )

                        log_activity(f"Completed general expert analysis, saved to {saved_paths['txt']}, {saved_paths['md']}, {saved_paths['pdf']}", st.session_state.base_dir)
                        st.success(f"✅ Analysis complete! Saved to:\n- `{saved_paths['txt'].name}`\n- `{saved_paths['md'].name}`\n- `{saved_paths['pdf'].name}`")


                        
                        log_activity(f"Completed general expert analysis, saved to {saved_path}", st.session_state.base_dir)
                        st.success(f"✅ Analysis complete! Saved to: `{saved_path}`")
                        
                except Exception as e:
                    st.error(f"❌ Error during general expert analysis: {str(e)}")
                    log_activity(f"Error in general expert analysis: {str(e)}", st.session_state.base_dir)
                finally:
                    st.session_state.processing_general = False
                    st.rerun()
        
        # Results section
        st.subheader("📈 Expert Insights Preview")
        general_dir = st.session_state.base_dir / "general_experts"
        if general_dir.exists():
            files = sorted(general_dir.glob("*.txt"), key=os.path.getmtime, reverse=True)
            if files:
                latest_file = files[0]
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                preview = content[:500] + "..." if len(content) > 500 else content
                st.text_area("Preview", preview, height=200, key="general_preview")
                if st.button("📄 View Full Analysis", key="general_view"):
                    st.text_area("Full Analysis", content, height=400, key="general_full")

    # Tab 3: Podcast Analysis
    with tab3:
        st.header("🎙️ Podcast Analysis with TSI Integration")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Podcast Configuration")
            st.write("🔗 Enter YouTube Links (Videos or Channels) for Transcription and Analysis:")
            
            podcast_links_input = st.text_area(
                "Paste YouTube Links (one per line)",
                placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...",
                key="podcast_links_input"
            )
            
            podcast_links = [link.strip() for link in podcast_links_input.splitlines() if link.strip()]
            
            date_range = st.date_input(
                "Analysis Period (for context only)",
                value=[datetime.now() - timedelta(days=7), datetime.now()],
                help="Select the date range for episode analysis",
                key="podcast_date_range"
            )
            
            st.subheader("Analysis Options")
            include_tsi = st.checkbox("Include TSI Framework Integration", value=True, key="podcast_tsi")
            include_astrology = st.checkbox("Include Astrology Analysis", value=False, key="podcast_astrology")
            max_bullets = st.slider("Maximum Bullets per Topic", 50, 150, 100, key="podcast_bullets")
        
        with col2:
            st.subheader("TSI Integration")
            st.info("🔮 TSI Model will be applied to correlate insights with systemic stress indicators")
            
            investment_horizon = st.selectbox(
                "Investment Horizon",
                ["1-3 months", "3-6 months", "6-12 months"],
                index=1,
                key="podcast_horizon"
            )
            
            # Status indicator
            if st.session_state.processing_podcast:
                st.error("🔄 Processing...")
            else:
                st.success("✅ Ready")
            
            # Run button
            run_podcast = st.button(
                "🚀 Run Podcast Analysis",
                disabled=st.session_state.processing_podcast or not podcast_links or any([
                    st.session_state.processing_paywalled,
                    st.session_state.processing_general,
                    st.session_state.processing_suite
                ]),
                use_container_width=True,
                key="btn_podcast"
            )
            
            # Process podcast analysis
            if run_podcast and podcast_links:
                st.session_state.processing_podcast = True
                try:
                    with st.spinner("Transcribing and analyzing podcast episodes..."):
                        log_activity(f"Started podcast analysis for provided links", st.session_state.base_dir)
                        
                        # Run the agent
                        result = asyncio.run(st.session_state.agents.run_podcast_agent(
                            podcast_links=podcast_links
                        ))
                        
                        # Save result
                        filename = f"podcast_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        # saved_path = save_document(
                        #     result, 
                        #     filename, 
                        #     "podcast_analysis", 
                        #     st.session_state.base_dir
                        # )
                        saved_paths = save_document_all_formats(
                            result, 
                            filename, 
                            "podcast_analysis", 
                            st.session_state.base_dir
                        )
                        
                        log_activity(f"Completed podcast analysis, saved to {saved_paths}", st.session_state.base_dir)
                        st.success(f"✅ Podcast analysis complete! Saved to: `{saved_paths}`")
                        
                except Exception as e:
                    st.error(f"❌ Error during podcast analysis: {str(e)}")
                    log_activity(f"Error in podcast analysis: {str(e)}", st.session_state.base_dir)
                finally:
                    st.session_state.processing_podcast = False
                    st.rerun()
        
        # TSI Dashboard
        st.subheader("📊 TSI Dashboard")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Geopolitical Tension", "7.2", "↑ 0.8")
        with col2:
            st.metric("Debt Stress", "8.1", "↑ 1.2")
        with col3:
            st.metric("Currency Instability", "6.5", "↓ 0.3")
        
        # Results section
        st.subheader("🎧 Podcast Insights Preview")
        podcast_dir = st.session_state.base_dir / "podcast_analysis"
        if podcast_dir.exists():
            files = sorted(podcast_dir.glob("*.txt"), key=os.path.getmtime, reverse=True)
            if files:
                latest_file = files[0]
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                preview = content[:500] + "..." if len(content) > 500 else content
                st.text_area("Preview", preview, height=200, key="podcast_preview")
                if st.button("📄 View Full Transcript & Analysis", key="podcast_view"):
                    st.text_area("Full Analysis", content, height=400, key="podcast_full")

    # Tab 4: Combined Dashboard
    with tab4:
        st.header("📋 Combined Analysis Dashboard")

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Analyses", "12", "↑ 3")
        with col2:
            st.metric("Documents Generated", "45", "↑ 8")
        with col3:
            st.metric("Processing Time", "2.3s", "↓ 0.5s")
        with col4:
            st.metric("Success Rate", "98%", "↑ 2%")

        st.divider()

        # Recent activity
        st.subheader("📈 Recent Activity")
        log_file = st.session_state.base_dir / "logs" / f"activity_{datetime.now().strftime('%Y%m%d')}.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            for log_entry in logs[-10:]:
                st.text(log_entry.strip())

        st.divider()

        # Complete suite
        st.subheader("🚀 Run Complete Analysis Suite")
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("Run all three agents in sequence with predefined configurations:")
            suite_config = {
                "Paywalled": "Tier 1 experts (10 bullets each)",
                "General": "Top 5 market experts (5 bullets each)",
                "Podcast": "Capital Cosm + TSI integration"
            }
            for agent, config in suite_config.items():
                st.write(f"• **{agent}**: {config}")

        with col2:
            # Status indicator
            if st.session_state.processing_suite:
                st.error("🔄 Processing Suite...")
            else:
                st.success("✅ Ready")

            # Run complete suite button
            run_suite = st.button(
                "🚀 Run Complete Suite",
                use_container_width=True,
                disabled=st.session_state.processing_suite or any([
                    st.session_state.processing_paywalled,
                    st.session_state.processing_general,
                    st.session_state.processing_podcast
                ]),
                key="btn_suite"
            )

            # Process complete suite
            if run_suite:
                st.session_state.processing_suite = True
                try:
                    st.info("🔄 Running complete analysis suite... This may take several minutes.")
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Run paywalled analysis (sync call)
                    status_text.text("Running paywalled content analysis...")
                    log_activity("Started complete suite - paywalled analysis", st.session_state.base_dir)
                    result1 = st.session_state.agents.run_paywalled_agent(
                        content_sources=[selected_pdf],
                        expert_tier=expert_tier
                    )
                    # save_document(result1, "paywalled_suite_analysis.txt", "combined_analysis", st.session_state.base_dir)
                    saved_paths = save_document_all_formats(
                            result1, 
                            "paywalled_suite_analysis", 
                            "combined_analysis", 
                            st.session_state.base_dir
                        )
                    progress_bar.progress(33)

                    # Run general expert analysis (async)
                    status_text.text("Analyzing general experts...")
                    log_activity("Suite - running general expert analysis", st.session_state.base_dir)
                    result2 = asyncio.run(st.session_state.agents.run_general_expert_agent(
                        expert_names=["Bob Moriarty", "Kitco News", "Mike Maloney", "Peter Schiff", "Silver Institute"],
                        time_frame="Last 7 days",
                        focus_areas=["Precious Metals", "Crypto", "Macro Economics", "Geopolitics", "Energy"]
                    ))
                    # save_document(result2, "general_suite_analysis.txt", "combined_analysis", st.session_state.base_dir)
                    saved_paths = save_document_all_formats(
                            result2, 
                            "general_suite_analysis", 
                            "combined_analysis", 
                            st.session_state.base_dir
                        )
                    progress_bar.progress(66)

                    # Run podcast analysis (async)
                    status_text.text("Processing podcast analysis with TSI...")
                    log_activity("Suite - running podcast analysis", st.session_state.base_dir)
                    result3 = asyncio.run(st.session_state.agents.run_podcast_agent(
                        podcast_links=podcast_links
                    ))
                    # save_document(result3, "podcast_suite_analysis.txt", "combined_analysis", st.session_state.base_dir)
                    saved_paths = save_document_all_formats(
                            result3, 
                            "podcast_suite_analysis", 
                            "combined_analysis", 
                            st.session_state.base_dir
                        )
                    progress_bar.progress(100)

                    status_text.text("✅ Complete analysis suite finished!")
                    log_activity("Complete suite finished successfully", st.session_state.base_dir)
                    st.success("All analyses completed successfully!")

                except Exception as e:
                    st.error(f"❌ Error during suite execution: {str(e)}")
                    log_activity(f"Error in complete suite: {str(e)}", st.session_state.base_dir)
                finally:
                    st.session_state.processing_suite = False
                    st.rerun()

    # Tab 5: File Manager
    with tab5:
        st.header("📁 Document Manager")

        # Storage overview
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📊 Storage Overview")
            dirs = ["paywalled_content", "general_experts", "podcast_analysis", "combined_analysis"]
            storage_data = []
            for directory in dirs:
                dir_path = st.session_state.base_dir / directory
                if dir_path.exists():
                    file_count = len(list(dir_path.glob("*.txt")))
                    total_size = sum(f.stat().st_size for f in dir_path.glob("*.txt")) / 1024
                else:
                    file_count = 0
                    total_size = 0
                storage_data.append({
                    "Directory": directory.replace("_", " ").title(),
                    "Files": file_count,
                    "Size (KB)": round(total_size, 2)
                })
            df = pd.DataFrame(storage_data)
            st.dataframe(df, use_container_width=True)

        with col2:
            st.subheader("🧹 Cleanup Tools")
            cleanup_older_than = st.selectbox(
                "Delete files older than:",
                ["1 day", "3 days", "1 week", "1 month"],
                key="cleanup_time"
            )
            if st.button("🗑️ Cleanup Old Files", use_container_width=True, key="cleanup_btn"):
                st.warning("Cleanup functionality would be implemented here")

            st.divider()
            st.subheader("📤 Export Options")
            export_format = st.selectbox(
                "Export Format",
                ["ZIP Archive", "PDF Report", "Excel Summary"],
                key="export_format"
            )
            if st.button("📦 Export All", use_container_width=True, key="export_btn"):
                st.info("Export functionality would be implemented here")

        # File browser
        st.subheader("🗂️ File Browser")

        # Dynamically include subfolders for paywalled_content
        root_dirs = ["paywalled_content", "general_experts", "podcast_analysis", "combined_analysis", "logs"]
        browse_options = []

        for d in root_dirs:
            path = st.session_state.base_dir / d
            if d == "paywalled_content" and path.exists():
                browse_options.extend([str(p.relative_to(st.session_state.base_dir)) for p in path.glob("**/") if p.is_dir()])
            elif path.exists():
                browse_options.append(d)

        selected_dir = st.selectbox("Browse Directory", browse_options, key="browse_dir")
        dir_path = st.session_state.base_dir / selected_dir

        if dir_path.exists():
            files = sorted(dir_path.glob("*.*"), key=os.path.getmtime, reverse=True)
            if files:
                file_data = []
                for file_path in files:
                    stat = file_path.stat()
                    file_data.append({
                        "Filename": file_path.name,
                        "Size (KB)": round(stat.st_size / 1024, 2),
                        "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })

                df_files = pd.DataFrame(file_data)
                selected_file_idx = st.selectbox(
                    "Select file to preview:",
                    range(len(df_files)),
                    format_func=lambda x: df_files.iloc[x]["Filename"],
                    key="file_selector"
                )

                if selected_file_idx is not None:
                    selected_file_path = files[selected_file_idx]
                    col1, col2, col3 = st.columns([1, 1, 1])

                    with col1:
                        if st.button("👁️ Preview", key="preview_btn"):
                            try:
                                with open(selected_file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                preview = content[:1000] + "..." if len(content) > 1000 else content
                                st.text_area("File Preview", preview, height=300, key="file_preview")
                            except Exception as e:
                                st.error(f"Error reading file: {str(e)}")

                    with col2:
                        if st.button("📥 Download", key="download_btn"):
                            try:
                                with open(selected_file_path, 'rb') as f:
                                    binary_content = f.read()
                                mime_type, _ = mimetypes.guess_type(str(selected_file_path))
                                if mime_type is None:
                                    mime_type = "application/octet-stream"
                                st.download_button(
                                    label="Download File",
                                    data=binary_content,
                                    file_name=selected_file_path.name,
                                    mime=mime_type,
                                    key="download_file"
                                )
                            except Exception as e:
                                st.error(f"Error preparing download: {str(e)}")

                    with col3:
                        if st.button("🗑️ Delete", type="secondary", key="delete_btn"):
                            if st.checkbox(f"Confirm delete {selected_file_path.name}", key="delete_confirm"):
                                try:
                                    selected_file_path.unlink()
                                    st.success("File deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting file: {str(e)}")

                st.dataframe(df_files, use_container_width=True)
            else:
                st.info(f"No files found in {selected_dir}")
        else:
            st.warning(f"Directory {selected_dir} does not exist")


    # # Tab 5: File Manager
    # with tab5:
    #     st.header("📁 Document Manager")
        
    #     # Storage overview
    #     col1, col2 = st.columns([1, 1])
    #     with col1:
    #         st.subheader("📊 Storage Overview")
    #         dirs = ["paywalled_content", "general_experts", "podcast_analysis", "combined_analysis"]
    #         storage_data = []
    #         for directory in dirs:
    #             dir_path = st.session_state.base_dir / directory
    #             if dir_path.exists():
    #                 file_count = len(list(dir_path.glob("*.txt")))
    #                 total_size = sum(f.stat().st_size for f in dir_path.glob("*.txt")) / 1024
    #             else:
    #                 file_count = 0
    #                 total_size = 0
    #             storage_data.append({
    #                 "Directory": directory.replace("_", " ").title(),
    #                 "Files": file_count,
    #                 "Size (KB)": round(total_size, 2)
    #             })
    #         df = pd.DataFrame(storage_data)
    #         st.dataframe(df, use_container_width=True)
        
    #     with col2:
    #         st.subheader("🧹 Cleanup Tools")
    #         cleanup_older_than = st.selectbox(
    #             "Delete files older than:",
    #             ["1 day", "3 days", "1 week", "1 month"],
    #             key="cleanup_time"
    #         )
    #         if st.button("🗑️ Cleanup Old Files", use_container_width=True, key="cleanup_btn"):
    #             st.warning("Cleanup functionality would be implemented here")
            
    #         st.divider()
    #         st.subheader("📤 Export Options")
    #         export_format = st.selectbox(
    #             "Export Format",
    #             ["ZIP Archive", "PDF Report", "Excel Summary"],
    #             key="export_format"
    #         )
    #         if st.button("📦 Export All", use_container_width=True, key="export_btn"):
    #             st.info("Export functionality would be implemented here")
        

    #     # File browser
    #     st.subheader("🗂️ File Browser")
    #     selected_dir = st.selectbox(
    #         "Browse Directory",
    #         ["paywalled_content", "general_experts", "podcast_analysis", "combined_analysis", "logs"],
    #         key="browse_dir"
    #     )
        
    #     dir_path = st.session_state.base_dir / selected_dir
    #     if dir_path.exists():
    #         files = sorted(dir_path.glob("*.*"), key=os.path.getmtime, reverse=True)
    #         if files:
    #             file_data = []
    #             for file_path in files:
    #                 stat = file_path.stat()
    #                 file_data.append({
    #                     "Filename": file_path.name,
    #                     "Size (KB)": round(stat.st_size / 1024, 2),
    #                     "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    #                 })
                
    #             df_files = pd.DataFrame(file_data)
    #             selected_file_idx = st.selectbox(
    #                 "Select file to preview:",
    #                 range(len(df_files)),
    #                 format_func=lambda x: df_files.iloc[x]["Filename"],
    #                 key="file_selector"
    #             )
                
    #             if selected_file_idx is not None:
    #                 selected_file_path = files[selected_file_idx]
    #                 col1, col2, col3 = st.columns([1, 1, 1])
                    
    #                 with col1:
    #                     if st.button("👁️ Preview", key="preview_btn"):
    #                         try:
    #                             with open(selected_file_path, 'r', encoding='utf-8') as f:
    #                                 content = f.read()
    #                             preview = content[:1000] + "..." if len(content) > 1000 else content
    #                             st.text_area("File Preview", preview, height=300, key="file_preview")
    #                         except Exception as e:
    #                             st.error(f"Error reading file: {str(e)}")
                    
    #                 with col2:
    #                     if st.button("📥 Download", key="download_btn"):
    #                         try:
    #                             with open(selected_file_path, 'r', encoding='utf-8') as f:
    #                                 content = f.read()
    #                             st.download_button(
    #                                 label="Download File",
    #                                 data=content,
    #                                 file_name=selected_file_path.name,
    #                                 mime="text/plain",
    #                                 key="download_file"
    #                             )
    #                         except Exception as e:
    #                             st.error(f"Error preparing download: {str(e)}")
                    
    #                 with col3:
    #                     if st.button("🗑️ Delete", type="secondary", key="delete_btn"):
    #                         if st.checkbox(f"Confirm delete {selected_file_path.name}", key="delete_confirm"):
    #                             try:
    #                                 selected_file_path.unlink()
    #                                 st.success("File deleted successfully!")
    #                                 st.rerun()
    #                             except Exception as e:
    #                                 st.error(f"Error deleting file: {str(e)}")
                
    #             st.dataframe(df_files, use_container_width=True)
    #         else:
    #             st.info(f"No files found in {selected_dir}")
    #     else:
    #         st.warning(f"Directory {selected_dir} does not exist")

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🚀 Investment Research AI Agents | Built with Streamlit & LangGraph by *Jawad*</p>
        <p>📊 TSI Framework Integration | 🤖 Powered by AI Agents</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()