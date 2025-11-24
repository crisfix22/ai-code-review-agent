# AI Code Review Agent

An AI-powered code review bot that automatically analyzes pull requests and provides detailed feedback on potential issues, best practices, and optimizations.
This bot supports multiple AI providers (OpenAI, Google Gemini, Anthropic Claude) and can be easily integrated into any repository via GitHub Actions.
Developers can extend it with new prompts, custom rules, or AI models to adapt it to different languages or team standards.

**Keywords**: AI code review, automated code review, GitHub Actions bot, code analysis, pull request review, AI code analyzer, code quality checker, GPT-4 code review, Claude code review, Gemini code review, Python code review, React code review, CI/CD code review, FastAPI code review service, AI Agent, AI Bot

## Features

- 🤖 **Multi-Provider AI Support**: Choose from OpenAI (GPT-4), Google Gemini, or Anthropic Claude
- 🔍 **Automatic Language Detection**: Automatically detects programming language from code diffs
- 📝 **Comprehensive Code Review**: Analyzes code for bugs, security issues, performance, best practices, and maintainability
- 🧠 **RAG (Retrieval Augmented Generation)**: Uses Langchain and ChromaDB to enhance analysis with context from previous reviews and documentation
- 🔗 **GitHub Integration**: Easy integration with GitHub Actions workflows
- 🐳 **Docker Support**: Ready for deployment to Google Cloud Run or any container platform
- 📱 **Multi-Channel Notifications**: Optional integrations with Google Chat and WhatsApp

## Architecture

The service exposes a REST API endpoint that accepts code diffs (base64 encoded) and returns AI-generated code review feedback. It's designed to work with CI/CD pipelines, particularly GitHub Actions.

```
GitHub PR → GitHub Actions → API Endpoint → AI Provider → Code Review Feedback
```

## Installation

### Prerequisites

- Python 3.11 or higher
- pip or uv package manager
- (Optional) ngrok for local development with GitHub webhooks

### Local Installation

1. Clone the repository:
```bash
git clone https://github.com/crisfix22/ai-code-review-agent.git
cd ai-code-review-agent
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file (see Configuration section below):
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Local Development

The project includes two helper scripts for local development:

### Starting the Server

Use `run_server.sh` to start the FastAPI server locally on port 8080:

```bash
./run_server.sh
```

Or manually:
```bash
uvicorn main:app --reload --port 8080
```

The server will be available at `http://localhost:8080`.

### Exposing Local Server to Internet (ngrok)

For local development with GitHub webhooks, you need to expose your local server to the internet. The project includes `run_ngrok.sh` which uses ngrok for this purpose.

#### What is ngrok?

ngrok is a tool that creates a secure tunnel from a public URL to your local machine. This is essential for local development because:

- GitHub webhooks need to reach your server via a public URL
- You can test GitHub Actions integration without deploying to production
- It provides HTTPS endpoints automatically

#### Installing ngrok

1. **macOS** (using Homebrew):
```bash
brew install ngrok/ngrok/ngrok
```

2. **Linux**:
```bash
# Download from https://ngrok.com/download
# Or using snap:
snap install ngrok
```

3. **Windows**:
- Download from [ngrok.com/download](https://ngrok.com/download)
- Extract and add to PATH

4. **Sign up and get authtoken**:
```bash
# Sign up at https://dashboard.ngrok.com/signup
# Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_AUTHTOKEN
```

#### Using ngrok with this project

1. Start the server in one terminal:
```bash
./run_server.sh
```

2. In another terminal, expose it with ngrok:
```bash
./run_ngrok.sh
```

The script will output a public URL like `https://xxxx-xx-xx-xx-xx.ngrok-free.app` that forwards to your local `localhost:8080`.

**Note**: Update the URL in your GitHub Actions workflow to use the ngrok URL instead of `https://your.domain.com/analize`.

## Configuration

Create a `.env` file in the project root with the following variables:

### Required (at least one AI provider)

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o  # Optional, defaults to gpt-4o

# OR Google Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash  # Optional, defaults to gemini-2.5-flash

# OR Anthropic Claude Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CLAUDE_MODEL=claude-sonnet-4-5  # Optional, defaults to claude-sonnet-4-5
```

### Optional

```env
# Enable/Disable Notifications
SEND_WHATSAPP=true  # Set to true to enable WhatsApp notifications
SEND_GOOGLE_CHAT=true  # Set to true to enable Google Chat notifications

# Google Chat Webhook (for notifications)
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/...

# WhatsApp Business API (for notifications)
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_RECIPIENT_PHONE=1234567890  # Country code + number without +
WHATSAPP_API_VERSION=v18.0  # Optional, defaults to v18.0

# RAG Configuration (Optional)
USE_RAG=true  # Enable/disable RAG (default: true)
VECTOR_DB_TYPE=chroma  # Vector database type (default: chroma)
CHROMA_DB_PATH=./chroma_db  # Path for ChromaDB storage (default: ./chroma_db)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # Optional, for OpenAI embeddings
```

See `.env.example` for a complete template.

## Setting Up Notifications

The service supports sending code review notifications to WhatsApp and Google Chat. To enable notifications, you must:

1. Set the corresponding environment variable to `true`:
   - `SEND_WHATSAPP=true` for WhatsApp notifications
   - `SEND_GOOGLE_CHAT=true` for Google Chat notifications

2. Configure the required credentials for each service (see below)

### Configuring WhatsApp Business API

To send notifications via WhatsApp, you need to set up a WhatsApp Business API account through Meta (Facebook) for Developers.

#### Step 1: Create a Meta Developer Account

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Sign in with your Facebook account or create a new account
3. Click "My Apps" → "Create App"

#### Step 2: Set Up WhatsApp Business API

1. Select "Business" as the app type
2. Fill in your app details (name, contact email, etc.)
3. In the app dashboard, go to "WhatsApp" → "Getting Started"
4. Follow the setup wizard to:
   - Accept the WhatsApp Business API Terms of Service
   - Add a phone number (you can use a test number initially)
   - Verify your phone number

#### Step 3: Get Your Credentials

1. **Access Token**:
   - Go to "WhatsApp" → "API Setup"
   - Copy the "Temporary access token" (for testing)
   - For production, create a System User and generate a permanent token:
     - Go to "Business Settings" → "Users" → "System Users"
     - Create a new system user with "Developer" role
     - Generate a token with `whatsapp_business_messaging` and `whatsapp_business_management` permissions

2. **Phone Number ID**:
   - In "WhatsApp" → "API Setup"
   - Find your "Phone number ID" (it's a long numeric ID)

3. **Recipient Phone Number**:
   - The phone number where you want to receive notifications
   - Format: Country code + number without + sign
   - Example: `5491123456789` for Argentina

#### Step 4: Configure Environment Variables

Add these to your `.env` file:

```env
SEND_WHATSAPP=true
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_RECIPIENT_PHONE=1234567890
WHATSAPP_API_VERSION=v18.0
```

#### Important Notes

- **Test Mode**: Initially, you can only send messages to verified phone numbers (numbers you've added in the Meta dashboard)
- **Production**: To send messages to any number, you need to:
  - Complete business verification
  - Submit your app for review
  - Get approved for production use
- **Rate Limits**: Free tier has rate limits. Check [WhatsApp API documentation](https://developers.facebook.com/docs/whatsapp/cloud-api) for details

### Configuring Google Chat Webhooks

To send notifications via Google Chat, you need to create a webhook in a Google Chat space.

#### Step 1: Create a Google Chat Space

1. Open [Google Chat](https://chat.google.com/)
2. Create a new space or use an existing one
3. Click on the space name → "Apps and integrations"

#### Step 2: Add Incoming Webhook

1. In the space settings, click "Configure webhooks"
2. Click "Add webhook" or "Manage webhooks"
3. Give your webhook a name (e.g., "Code Review Bot")
4. Click "Save"
5. Copy the webhook URL (it looks like: `https://chat.googleapis.com/v1/spaces/XXXXX/messages?key=YYYYY&token=ZZZZZ`)

#### Step 3: Configure Environment Variables

Add these to your `.env` file:

```env
SEND_GOOGLE_CHAT=true
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/XXXXX/messages?key=YYYYY&token=ZZZZZ
```

#### Important Notes

- The webhook URL contains sensitive credentials - keep it secure
- Anyone with the webhook URL can send messages to your space
- You can create multiple webhooks for different spaces
- Webhooks don't require authentication beyond the URL token

## Usage

### API Endpoint

**POST** `/analize`

Analyzes a code diff and returns AI-generated feedback.

**Request Body:**
```json
{
  "pr_number": 123,
  "repo": "owner/repo",
  "title": "Add new feature",
  "url": "https://github.com/owner/repo/pull/123",
  "author": "username",
  "diff_b64": "base64_encoded_diff_here",
  "provider": "openai",  // Optional: "openai", "gemini", "claude", "auto", or omit for auto-selection
  "language": "python",  // Optional: auto-detected if not provided
  "use_rag": true        // Optional: enable/disable RAG for this request (default: true)
}
```

**Provider Options:**
- `"openai"`: Use OpenAI (GPT-4)
- `"gemini"`: Use Google Gemini
- `"claude"`: Use Anthropic Claude
- `"auto"`: Automatically select the first available provider (priority: OpenAI → Claude → Gemini)
- Omit or `null`: Same as `"auto"` (default behavior)

**Response:**
```json
{
  "feedback": "AI-generated code review feedback..."
}
```

### GitHub Actions Integration

1. Copy the example workflow to your repository:
```bash
cp github_workflow.example.yml .github/workflows/ai-code-review.yml
```

2. Update the workflow file:
   - Change the branch name if needed (default is `develop`)
   - Update the API endpoint URL to your deployed service
   - Optionally set `PROVIDER` and `LANGUAGE` environment variables

3. The workflow will automatically:
   - Calculate the diff when a PR is opened, updated, or reopened
   - Send it to the AI code review service
   - Post the feedback as a comment on the PR

### Example Workflow

See `github_workflow.example.yml` for a complete example. The workflow:
- Triggers on PR events (opened, synchronize, reopened)
- Calculates the diff between base and head commits
- Encodes it as base64
- Sends it to your API endpoint
- Posts the feedback as a PR comment

## Deployment

### Docker

Build the Docker image:
```bash
docker build -t ai-code-review .
```

Run locally:
```bash
docker run -p 8080:8080 --env-file .env ai-code-review
```

### Google Cloud Run

1. Build and push to Google Container Registry:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/ai-code-review
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy ai-code-review \
  --image gcr.io/PROJECT_ID/ai-code-review \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=your_key"
```

3. Update your GitHub Actions workflow with the Cloud Run URL.

## Supported Languages

The service automatically detects the programming language from the diff, but you can also specify it explicitly. Currently optimized prompts are available for:

- **Python**: PEP 8 compliance, type hints, best practices
- **React**: Hooks, performance, component structure
- **React Native**: Platform-specific considerations, navigation, mobile optimizations

Other languages will use the Python prompt template as a fallback.

## How It Works

1. **Diff Encoding**: GitHub Actions calculates the diff and encodes it as base64
2. **API Request**: The encoded diff is sent to the `/analize` endpoint
3. **Language Detection**: The service detects the programming language from file extensions
4. **RAG Context Retrieval** (if enabled): Similar previous reviews and documentation are retrieved from ChromaDB
5. **Prompt Enrichment**: The prompt is enriched with relevant context from RAG
6. **AI Analysis**: The appropriate AI provider analyzes the code using language-specific prompts with context
7. **Feedback Generation**: The AI generates comprehensive code review feedback
8. **Storage**: The review is stored in ChromaDB for future reference
9. **Response**: Feedback is returned and posted as a PR comment

## RAG (Retrieval Augmented Generation)

This project includes RAG capabilities using Langchain and ChromaDB to enhance code analysis with context from:
- Previous code reviews
- Code snippets and best practices
- Technical documentation

RAG is enabled by default but can be disabled per-request or globally. See [RAG.md](RAG.md) for detailed documentation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI providers: OpenAI, Google Gemini, Anthropic Claude

## Topics & Keywords

This project is related to the following topics and can be found by searching for:

- **AI & Machine Learning**: `ai-code-review`, `automated-code-review`, `ai-code-analyzer`, `machine-learning`, `artificial-intelligence`
- **Code Quality**: `code-review`, `code-analysis`, `code-quality`, `static-analysis`, `code-reviewer`, `pull-request-review`
- **GitHub Integration**: `github-actions`, `github-bot`, `github-integration`, `pr-review`, `pull-request-bot`
- **CI/CD**: `cicd`, `continuous-integration`, `automated-testing`, `devops`, `code-review-automation`
- **AI Providers**: `openai`, `gpt-4`, `claude`, `anthropic`, `gemini`, `google-ai`
- **Languages**: `python`, `react`, `react-native`, `javascript`, `typescript`, `code-review-python`
- **Tools & Frameworks**: `fastapi`, `docker`, `rest-api`, `webhook`, `github-webhook`
- **Notifications**: `whatsapp-integration`, `google-chat`, `slack-alternative`, `notification-service`

**Search terms**: code review bot, AI code reviewer, automated PR review, GitHub code review automation, AI-powered code analysis, code review service, pull request analyzer, code quality bot, AI code inspection, automated code feedback, AI Agent, AI Bot

