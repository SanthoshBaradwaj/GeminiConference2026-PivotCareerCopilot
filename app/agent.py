# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_prompt import INSTRUCTION
from .a2ui_utils import a2ui_callback
from .career_tools import (
    analyze_ats_readiness,
    calculate_tiered_targeting,
    compile_master_plan,
    fetch_company_job_postings,
    fetch_github_profile_and_repos,
    filter_market_reality,
    generate_career_video_asset,
    generate_career_visual_asset,
    search_job_board_api,
    upload_tailored_resume_to_gcs,
)
from .firestore_tools import (
    add_intake_skill,
    add_to_shortlist,
    get_intake_profile,
    get_shortlist,
    get_target_tiers,
    save_target_tiers,
)

MODEL = "gemini-3.6-flash"
PROJECT_ID = "qwiklabs-gcp-04-2479ded67a3b"
AGENT_ENGINE_ID = "5949881829384257536"
LOCATION = "us-east1"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# WRITE: after each turn, send the session to Memory Bank for durable fact extraction
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        # Gracefully continue if memory service is initializing or unreachable
        print(f"Memory extraction notice: {e}")
    return None


# Memory service builder for deployment
def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=AGENT_ENGINE_ID,
    )


memory_service_builder = memory_bank_service_builder

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        calculate_tiered_targeting,
        analyze_ats_readiness,
        generate_career_visual_asset,
        generate_career_video_asset,
        fetch_github_profile_and_repos,
        fetch_company_job_postings,
        filter_market_reality,
        search_job_board_api,
        compile_master_plan,
        upload_tailored_resume_to_gcs,
        get_target_tiers,
        save_target_tiers,
        get_shortlist,
        add_to_shortlist,
        get_intake_profile,
        add_intake_skill,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
