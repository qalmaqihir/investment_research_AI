##################################### ------ {YT with Links Integrated - Live Agent V2} ------#####################################


import os
import asyncio
import logging
from typing import Dict, List, Any, TypedDict, Optional
from datetime import datetime, timedelta
import json
import re

# YouTube and transcription imports
import yt_dlp
import whisper
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import requests
from urllib.parse import urlparse, parse_qs

from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
# from openai import OpenAI ## we have to use chat.completion method, there is no invoke mehth
from langchain_openai import ChatOpenAI ## here now we can use the invoke method...

from langgraph.graph import StateGraph, END
from datetime import datetime, timezone

# Setup dedicated logger for this class
logger = logging.getLogger("podcast_agent")
logger.setLevel(logging.INFO)

# Ensure no duplicate handlers if imported multiple times
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [PodcastAgent] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class PodcastState(TypedDict):
    podcast_links: List[str]
    channel_videos: List[Dict[str, Any]]
    transcripts: List[Dict[str, Any]]
    summaries: List[Dict[str, Any]]
    tsi_analysis: str
    final_output: str

class YouTubeProcessor:
    """Handles YouTube video fetching and transcription"""
    
    def __init__(self):
        # Initialize Whisper model for fallback transcription
        try:
            self.whisper_model = whisper.load_model("base")
        except:
            self.whisper_model = None
            logger.warning("Whisper model not loaded - will rely on YouTube transcripts only")
    
    def extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from various YouTube URL formats"""
        try:
            # Handle different YouTube URL formats
            if '/channel/' in url:
                return url.split('/channel/')[1].split('/')[0]
            elif '/c/' in url or '/@' in url:
                # For custom URLs, we need to resolve them
                return self._resolve_channel_id(url)
            elif '/user/' in url:
                return self._resolve_channel_id(url)
            else:
                return None
        except Exception as e:
            logger.error(f"Error extracting channel ID from {url}: {str(e)}")
            return None
    
    def _resolve_channel_id(self, url: str) -> Optional[str]:
        """Resolve channel ID from custom URLs using yt-dlp"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('channel_id')
        except Exception as e:
            logger.error(f"Error resolving channel ID: {str(e)}")
            return None
    
    def get_latest_videos(self, channel_url: str, max_videos: int = 5) -> List[Dict[str, Any]]:
        """Get latest videos from a YouTube channel"""
        try:
            logger.info(f"Fetching latest videos from: {channel_url}")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlist_items': f'1:{max_videos}',  # Get first N videos
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Add /videos to channel URL to get videos playlist
                if not channel_url.endswith('/videos'):
                    if channel_url.endswith('/'):
                        channel_url += 'videos'
                    else:
                        channel_url += '/videos'
                
                playlist_info = ydl.extract_info(channel_url, download=False)
                
                videos = []
                if 'entries' in playlist_info:
                    for entry in playlist_info['entries'][:max_videos]:
                        if entry:
                            video_info = {
                                'video_id': entry.get('id'),
                                'title': entry.get('title', 'Unknown Title'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'duration': entry.get('duration', 0),
                                'upload_date': entry.get('upload_date', ''),
                                'channel': playlist_info.get('uploader', 'Unknown Channel'),
                                'channel_url': channel_url.replace('/videos', '')
                            }
                            videos.append(video_info)
                
                logger.info(f"Found {len(videos)} videos from channel")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching videos from {channel_url}: {str(e)}")
            return []
    
    def get_video_info(self, video_url: str) -> Dict[str, Any]:
        """Get detailed info for a single video"""
        try:
            video_id = self.extract_video_id(video_url)
            if not video_id:
                return {}
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                return {
                    'video_id': video_id,
                    'title': info.get('title', 'Unknown Title'),
                    'url': video_url,
                    'duration': info.get('duration', 0),
                    'upload_date': info.get('upload_date', ''),
                    'channel': info.get('uploader', 'Unknown Channel'),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0)
                }
        except Exception as e:
            logger.error(f"Error getting video info for {video_url}: {str(e)}")
            return {}
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        try:
            # Handle various YouTube URL formats
            if 'youtu.be/' in url:
                return url.split('youtu.be/')[1].split('?')[0]
            elif 'youtube.com/watch' in url:
                parsed = urlparse(url)
                return parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtube.com/embed/' in url:
                return url.split('youtube.com/embed/')[1].split('?')[0]
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID from {url}: {str(e)}")
            return None
    
    def get_transcript(self, video_url: str) -> Optional[str]:
        """Get transcript for a YouTube video"""
        try:
            video_id = self.extract_video_id(video_url)
            if not video_id:
                logger.error(f"Could not extract video ID from {video_url}")
                return None
            
            logger.info(f"Fetching transcript for video ID: {video_id}")
            
            # Try to get transcript using YouTube Transcript API
            try:
                # Get available transcripts
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Try to get English transcript first
                transcript = None
                try:
                    transcript = transcript_list.find_transcript(['en'])
                except:
                    # If English not available, get the first available transcript
                    try:
                        transcript = transcript_list.find_transcript(['en-US', 'en-GB'])
                    except:
                        # Get any available transcript
                        for t in transcript_list:
                            transcript = t
                            break
                
                if transcript:
                    transcript_data = transcript.fetch()
                    formatter = TextFormatter()
                    transcript_text = formatter.format_transcript(transcript_data)
                    logger.info(f"Successfully fetched transcript for {video_id}\nTranscript: {transcript_text[:1000]}...\n")
                    return transcript_text
                
            except Exception as e:
                logger.warning(f"YouTube Transcript API failed for {video_id}: {str(e)}")
                
                # Fallback to Whisper if available
                if self.whisper_model:
                    logger.info(f"Attempting Whisper transcription for {video_id}")
                    return self._transcribe_with_whisper(video_url)
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting transcript for {video_url}: {str(e)}")
            return None
    
    def _transcribe_with_whisper(self, video_url: str) -> Optional[str]:
        """Transcribe video using Whisper (fallback method)"""
        try:
            # Download audio using yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'temp_audio.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Find the downloaded audio file
            audio_file = None
            for ext in ['webm', 'mp4', 'm4a', 'mp3']:
                if os.path.exists(f'temp_audio.{ext}'):
                    audio_file = f'temp_audio.{ext}'
                    break
            
            if not audio_file:
                logger.error("Could not find downloaded audio file")
                return None
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(audio_file)
            
            # Clean up temporary file
            os.remove(audio_file)
            
            return result['text']
            
        except Exception as e:
            logger.error(f"Error transcribing with Whisper: {str(e)}")
            return None

class PodcastAgent:
    def __init__(self, llm_api_key: str):
        logger.info("Initializing PodcastAgent with DeepSeek Chat client.")
        # self.llm = ChatDeepSeek(
        #     model="deepseek-chat",
        #     temperature=0.5,
        #     max_tokens=None,
        #     timeout=None,
        #     max_retries=2,
        #     api_key=llm_api_key,
        # )
        # self.llm = OpenAI(api_key=llm_api_key)
        self.llm = ChatOpenAI(model="gpt-4o", api_key=llm_api_key)
        self.youtube_processor = YouTubeProcessor()
        self.tsi_model = """
        TSI Model: 3-circle Venn diagram with geopolitics (multipolar world with conflict), 
        macro (high debt leading to money printing and inflation), and AI+tech (deflation/depression).
        
        Components:
        1. Wealth Inequality: (GINI Coefficient × 0.5) + (Top 1% Wealth Share × 0.2)
        2. Debt Stress: (Total Debt/GDP × 0.3) + (Interest/Gov Revenue × 2)
        3. Tech Disruption: (Job Automation Rate × 3) + (Patent Growth Rate)^(0.5)
        4. Resource Concentration: HHI × (1 + tariff/sanction risk score)
        5. Currency Instability: (2 × Inflation Volatility) + (Reserve Decline) + (1.5 × REER Overvaluation) + (2 × Current Account Deficit) + (3 × Political Risk)
        6. Geopolitical Tension: (Alliance Breakdowns/Decade) + (Arms Sales Growth × 0.1)
        """

    def create_podcast_agent(self) -> StateGraph:
        def fetch_videos_from_links(state: PodcastState) -> PodcastState:
            logger.info(f"Processing {len(state['podcast_links'])} podcast links")
            all_videos = []
            
            for link in state['podcast_links']:
                logger.info(f"Processing link: {link}")
                
                # Check if it's a single video or channel
                if '/watch?v=' in link or 'youtu.be/' in link:
                    # Single video
                    video_info = self.youtube_processor.get_video_info(link)
                    if video_info:
                        all_videos.append(video_info)
                else:
                    # Channel or playlist
                    videos = self.youtube_processor.get_latest_videos(link, max_videos=2)
                    all_videos.extend(videos)
            
            state['channel_videos'] = all_videos
            logger.info(f"Fetched {len(all_videos)} total videos")
            return state

        def transcribe_videos(state: PodcastState) -> PodcastState:
            logger.info(f"Starting transcription for {len(state['channel_videos'])} videos")
            transcripts = []
            
            for video in state['channel_videos']:
                logger.info(f"Transcribing: {video['title']}")
                
                transcript_text = self.youtube_processor.get_transcript(video['url'])
                
                transcript_data = {
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'url': video['url'],
                    'channel': video['channel'],
                    'transcript': transcript_text or "Transcript not available",
                    'duration': video.get('duration', 0),
                    'upload_date': video.get('upload_date', '')
                }
                
                transcripts.append(transcript_data)
                logger.info(f"Completed transcription for: {video['title']}")
            
            state['transcripts'] = transcripts
            logger.info("Transcription complete for all videos")
            return state

        def summarize_transcripts(state: PodcastState) -> PodcastState:
            logger.info(f"Starting summarization for {len(state['transcripts'])} transcripts")
            summaries = []
            
            for transcript in state['transcripts']:
                if transcript['transcript'] and transcript['transcript'] != "Transcript not available":
                    logger.info(f"Summarizing: {transcript['title']}")
                    
                    # Create summary prompt
                    summary_prompt = f"""
                    Analyze this podcast/video transcript and provide a comprehensive summary with key insights.
                    Focus on:
                    - Main topics discussed
                    - Key insights and predictions
                    - Investment recommendations
                    - Economic/market analysis
                    - Notable quotes or statements
                    
                    Video Title: {transcript['title']}
                    Channel: {transcript['channel']}
                    
                    Transcript:
                    {transcript['transcript'][:10000]}  # Limit to avoid token limits
                    
                    Provide the summary in bullet points with the most important insights first.
                    """
                    
                    try:
                        response = self.llm.invoke([SystemMessage(content=summary_prompt)])
                        summary_text = response.content
                    except Exception as e:
                        logger.error(f"Error summarizing {transcript['title']}: {str(e)}")
                        summary_text = f"Summary generation failed: {str(e)}"
                    
                    summary = {
                        'video_id': transcript['video_id'],
                        'title': transcript['title'],
                        'channel': transcript['channel'],
                        'url': transcript['url'],
                        'summary': summary_text,
                        'duration': transcript['duration'],
                        'upload_date': transcript['upload_date']
                    }
                    
                    summaries.append(summary)
                    logger.info(f"Completed summary for: {transcript['title']}")
                else:
                    logger.warning(f"Skipping summary for {transcript['title']} - no transcript available")
            
            state['summaries'] = summaries
            logger.info("Summarization complete for all transcripts")
            return state

        def tsi_integration_analysis(state: PodcastState) -> PodcastState:
            logger.info("Starting TSI integration analysis")
            
            # Combine all summaries for TSI analysis
            all_summaries = ""
            for summary in state['summaries']:
                all_summaries += f"\n\n--- {summary['title']} ({summary['channel']}) ---\n"
                all_summaries += summary['summary']
            
            tsi_prompt = f"""
            Analyze the following podcast insights and integrate them with our TSI (Total Stress Index) framework:
            
            {self.tsi_model}
            
            Based on the podcast content and TSI framework, provide:
            1. Key insights organized by topic (macro, geopolitics, technology, markets, etc.)
            2. TSI stress indicators mentioned or implied in the content
            3. Investment recommendations for 1-6 month horizon
            4. Risk assessment based on TSI components
            
            Format as structured analysis with clear sections and bullet points.
            
            Podcast Content:
            {all_summaries}
            """
            
            try:
                response = self.llm.invoke([SystemMessage(content=tsi_prompt)])
                tsi_analysis = response.content
            except Exception as e:
                logger.error(f"Error in TSI analysis: {str(e)}")
                tsi_analysis = f"TSI analysis failed: {str(e)}"
            
            state['tsi_analysis'] = tsi_analysis
            logger.info("Completed TSI integration analysis")
            return state

        def compile_final_output(state: PodcastState) -> PodcastState:
            logger.info("Compiling final podcast analysis output")
            utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(f"Generating final analysis report.\nTime: {utc_now}\n")

            ## Output
            output = ""
            output = "# PODCAST ANALYSIS REPORT\n"
            output += "="*60 + "\n"
            output += f"**Report generated on:** {utc_now}\n\n"
            output += "## Channel Videos\n"
            for videos in state['channel_videos']:
                output += f"- {state['channel_videos']}\n"
            output+="\n"

            output += "## Prodcast Links\n"
            for podcast in state['podcast_links']:
                output += f"- {podcast}\n"
            output += "\n"
            output += "---\n\n"  # Horizontal line for separation

            
            # Summary statistics
            output += "## ANALYSIS SUMMARY\n"
            output += "-" * 30 + "\n"
            output += f"**Total Videos Analyzed: {len(state['summaries'])}**\n"
            output += f"**Channels Covered: {len(set(s['channel'] for s in state['summaries']))}**\n"
            output += f"**Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**\n\n"
            
            # Individual video summaries
            output += "## INDIVIDUAL VIDEO SUMMARIES\n"
            output += "-" * 40 + "\n\n"
            
            for i, summary in enumerate(state['summaries'], 1):
                output += f"{i}. **{summary['title']}**\n"
                output += f"   Channel: {summary['channel']}\n"
                output += f"   URL: {summary['url']}\n"
                output += f"   Duration: {summary['duration']} seconds\n"
                output += f"   Upload Date: {summary['upload_date']}\n\n"
                output += f"   Summary:\n"
                output += f"   {summary['summary']}\n"
                output += "\n" + "="*80 + "\n\n"
            
            # TSI Integration
            output += "# TSI FRAMEWORK INTEGRATION\n"
            output += "-" * 40 + "\n"
            output += state['tsi_analysis']
            output += "\n\n"
            
            # Footer
            output += "="*60 + "\n"
            output += "End of Podcast Analysis Report\n"
            output += "="*60 + "\n"
            
            state['final_output'] = output
            logger.info("Final podcast analysis output compilation complete")
            return state

        # Build the workflow
        workflow = StateGraph(PodcastState)
        workflow.add_node("fetch_videos", fetch_videos_from_links)
        workflow.add_node("transcribe_videos", transcribe_videos)
        workflow.add_node("summarize_transcripts", summarize_transcripts)
        workflow.add_node("tsi_analysis", tsi_integration_analysis)
        workflow.add_node("compile_output", compile_final_output)
        
        workflow.add_edge("fetch_videos", "transcribe_videos")
        workflow.add_edge("transcribe_videos", "summarize_transcripts")
        workflow.add_edge("summarize_transcripts", "tsi_analysis")
        workflow.add_edge("tsi_analysis", "compile_output")
        workflow.add_edge("compile_output", END)
        
        workflow.set_entry_point("fetch_videos")
        
        return workflow.compile()

    async def run(self, podcast_links: List[str]) -> str:
        logger.info(f"\t X<----> Starting PodcastAgent run for {len(podcast_links)} links. <---->X\n")
        
        agent = self.create_podcast_agent()
        initial_state = PodcastState(
            podcast_links=podcast_links,
            channel_videos=[],
            transcripts=[],
            summaries=[],
            tsi_analysis="",
            final_output=""
        )
        
        result = await agent.ainvoke(initial_state)
        logger.info(f"\t X<----> PodcastAgent run complete. <---->X\n")
        return result['final_output']

