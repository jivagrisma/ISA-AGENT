<div align="center">
  <img src="assets/ii.png" width="200"/>




# ISA - Intelligent System Agent

[![GitHub stars](https://img.shields.io/github/stars/jivagrisma/ISA-AGENT?style=social)](https://github.com/jivagrisma/ISA-AGENT/stargazers)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Status](https://img.shields.io/badge/Status-Fully%20Functional-green)](https://github.com/jivagrisma/ISA-AGENT)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock%20Nova%20Pro-orange)](https://aws.amazon.com/bedrock/)
</div>

ISA (Intelligent System Agent) is an open-source intelligent assistant designed to streamline and enhance workflows across multiple domains. It represents a significant advancement in how we interact with technology—shifting from passive tools to intelligent systems capable of independently executing complex tasks.

## 🚀 **CURRENT STATUS: FULLY FUNCTIONAL**

ISA is currently **100% operational** with the following active integrations:
- ✅ **Amazon Nova Pro** (AWS Bedrock) for advanced AI processing
- ✅ **Tavily API** for real-time web search capabilities
- ✅ **React/Next.js Frontend** with modern WebSocket communication
- ✅ **Automatic Web Search Detection** for up-to-date information



## Introduction
https://github.com/user-attachments/assets/d0eb7440-a6e2-4276-865c-a1055181bb33


## Overview

ISA is built around providing an agentic interface to advanced AI models. It offers:

- A simplified WebSocket server with direct AWS Bedrock integration
- A modern React-based frontend with real-time communication
- Integration with AWS Bedrock for access to Amazon Nova Pro
- Real-time web search capabilities through Tavily API
- Automatic detection of queries requiring current information

## Core Capabilities

ISA is a versatile open-source assistant built to elevate your productivity across domains:

| Domain | What ISA Can Do |
|--------|-----------------|
| Research & Fact‑Checking | **Real-time web search**, source triangulation, structured note‑taking, rapid summarization |
| Content Generation | Blog & article drafts, lesson plans, creative prose, technical manuals, Website creations |
| Current Information | **Automatic detection** of queries needing up-to-date info (anime releases, news, trends) |
| Software Development | Code synthesis, refactoring, debugging, test‑writing, and step‑by‑step tutorials |
| Workflow Automation | Script generation, browser automation, file management, process optimization |
| Problem Solving | Decomposition, alternative‑path exploration, stepwise guidance, troubleshooting |

## Methods

The ISA system represents a sophisticated approach to building versatile AI agents. Our methodology centers on:

1. **Core Agent Architecture and LLM Interaction**
   - System prompting with dynamically tailored context
   - Comprehensive interaction history management
   - Intelligent context management to handle token limitations
   - Systematic LLM invocation and capability selection
   - Iterative refinement through execution cycles

2. **Planning and Reflection**
   - Structured reasoning for complex problem-solving
   - Problem decomposition and sequential thinking
   - Transparent decision-making process
   - Hypothesis formation and testing

3. **Execution Capabilities**
   - File system operations with intelligent code editing
   - Command line execution in a secure environment
   - Advanced web interaction and browser automation
   - Task finalization and reporting
   - Specialized capabilities for various modalities (Experimental) (PDF, audio, image, video, slides)
   - Deep research integration

4. **Context Management**
   - Token usage estimation and optimization
   - Strategic truncation for lengthy interactions
   - File-based archival for large outputs

5. **Real-time Communication**
   - WebSocket-based interface for interactive use
   - Isolated agent instances per client
   - Streaming operational events for responsive UX

## GAIA Benchmark Evaluation

II-Agent has been evaluated on the GAIA benchmark, which assesses LLM-based agents operating within realistic scenarios across multiple dimensions including multimodal processing, tool utilization, and web searching.

We identified several issues with the GAIA benchmark during our evaluation:

- **Annotation Errors**: Several incorrect annotations in the dataset (e.g., misinterpreting date ranges, calculation errors)
- **Outdated Information**: Some questions reference websites or content no longer accessible
- **Language Ambiguity**: Unclear phrasing leading to different interpretations of questions

Despite these challenges, II-Agent demonstrated strong performance on the benchmark, particularly in areas requiring complex reasoning, tool use, and multi-step planning.

![GAIA Benchmark](assets/gaia.jpg)
You can view the full traces of some samples here: [GAIA Benchmark Traces](https://ii-agent-gaia.ii.inc/)

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend)
- AWS Account with Bedrock access
- Tavily API key for web search

## Environment

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# AWS Bedrock Configuration (Required)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# LLM Configuration
LLM_PROVIDER=bedrock
LLM_MODEL=nova-pro
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# Search Provider (Required for web search)
TAVILY_API_KEY=your_tavily_api_key

# Static Files
STATIC_FILE_BASE_URL=http://localhost:8001/

# Optional: Image and Video Generation
OPENAI_API_KEY=your_openai_key
OPENAI_AZURE_ENDPOINT=your_azure_endpoint
```

### Frontend Environment Variables

For the frontend, create a `.env` file in the frontend directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jivagrisma/ISA-AGENT.git
   cd ISA-AGENT
   ```

2. Set up Python environment:
   ```bash
   python -m venv venv_clean
   source venv_clean/bin/activate  # On Windows: venv_clean\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up frontend:
   ```bash
   cd frontend
   npm install
   ```

4. Configure environment variables (see Environment section above)

## Usage

### Quick Start (Recommended)

1. **Start the backend server:**
   ```bash
   source venv_clean/bin/activate
   python simple_server.py
   ```

2. **Start the frontend (in a separate terminal):**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open your browser to:** http://localhost:3001

### Features Available

- **💬 Interactive Chat**: Real-time conversation with ISA
- **🔍 Web Search**: Automatic detection and search for current information
- **📁 File Upload**: Support for document processing
- **💻 Code Integration**: VS Code workspace integration
- **🌐 Browser Tools**: Web browsing and interaction capabilities

## Project Structure

- `cli.py`: Command-line interface
- `ws_server.py`: WebSocket server for the frontend
- `src/ii_agent/`: Core agent implementation
  - `agents/`: Agent implementations
  - `llm/`: LLM client interfaces
  - `tools/`: Tool implementations
  - `utils/`: Utility functions

## Conclusion

The ISA framework, architected around the reasoning capabilities of Amazon Nova Pro through AWS Bedrock, presents a comprehensive and robust methodology for building versatile AI agents. Through its synergistic combination of a powerful LLM, real-time web search capabilities, an intuitive web interface, and intelligent context management strategies, ISA is well-equipped to address a wide spectrum of complex, multi-step tasks requiring both reasoning and current information. Its open-source nature and extensible design provide a strong foundation for continued research and development in the rapidly evolving field of agentic AI.

## 🎯 **Current Implementation Status**

ISA is **fully functional** and ready for production use with:
- ✅ **Amazon Nova Pro Integration**: Complete AWS Bedrock setup
- ✅ **Real-time Web Search**: Tavily API integration with automatic detection
- ✅ **Modern Web Interface**: React/Next.js frontend with WebSocket communication
- ✅ **File Processing**: Document upload and processing capabilities
- ✅ **Development Tools**: VS Code integration and terminal access

## Acknowledgement

We would like to express our sincere gratitude to the following projects and individuals for their invaluable contributions that have helped shape this project:

- **AugmentCode**: We have incorporated and adapted several key components from the [AugmentCode project](https://github.com/augmentcode/augment-swebench-agent). AugmentCode focuses on SWE-bench, a benchmark that tests AI systems on real-world software engineering tasks from GitHub issues in popular open-source projects. Their system provides tools for bash command execution, file operations, and sequential problem-solving capabilities designed specifically for software engineering tasks.

- **Manus**: Our system prompt architecture draws inspiration from Manus's work, which has helped us create more effective and contextually aware AI interactions.

- **Index Browser Use**: We have built upon and extended the functionality of the [Index Browser Use project](https://github.com/lmnr-ai/index/tree/main), particularly in our web interaction and browsing capabilities. Their foundational work has enabled us to create more sophisticated web-based agent behaviors.

We are committed to open source collaboration and believe in acknowledging the work that has helped us build this project. If you feel your work has been used in this project but hasn't been properly acknowledged, please reach out to us.

