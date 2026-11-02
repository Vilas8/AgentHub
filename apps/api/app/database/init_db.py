"""Database initialization and seeding for development."""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.agent import Agent, AgentVersion, AgentStatus, AgentVisibility, PricingType

logger = structlog.get_logger(__name__)


async def init_db(db: AsyncSession) -> None:
    """Seed initial data if tables are empty."""
    # Seed super admin only in non-production environments with a generated or explicit secret
    from app.core.config import settings
    result = await db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN))
    admin = result.scalar_one_or_none()

    if not admin:
        if settings.is_production:
            logger.warning("Production environment detected. Admin account creation skipped. Run bootstrap_admin CLI to initialize platform administrator.")
        else:
            logger.info("Seeding development super admin...")
            admin = User(
                email="admin@agenthub.example",
                hashed_password=hash_password("DevAdmin@AgentHub2026!"),
                full_name="Platform Admin",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            await db.flush()

    # Check categories
    cat_res = await db.execute(select(Category))
    categories = cat_res.scalars().all()
    cat_map = {c.slug: c for c in categories}

    if not categories:
        logger.info("Seeding categories...")
        cat_defs = [
            ("Productivity", "productivity", "Agents that automate daily tasks", "zap", 1),
            ("Research", "research", "Research and information gathering agents", "search", 2),
            ("Document Processing", "document-processing", "Extract and analyze documents", "file-text", 3),
            ("Customer Support", "customer-support", "Customer service automation agents", "headphones", 4),
            ("Sales & Marketing", "sales-marketing", "Lead generation and marketing agents", "trending-up", 5),
            ("Email", "email", "Email drafting and management agents", "mail", 6),
            ("Data Analysis", "data-analysis", "Data processing and analysis agents", "bar-chart", 7),
            ("Coding", "coding", "Code generation and review agents", "code", 8),
        ]
        for name, slug, desc, icon, order in cat_defs:
            c = Category(name=name, slug=slug, description=desc, icon=icon, sort_order=order)
            db.add(c)
            await db.flush()
            cat_map[slug] = c

    # Check 5 Platform Agents
    agent_check = await db.execute(select(Agent).where(Agent.is_platform_owned == True))
    if agent_check.scalars().first():
        logger.info("Platform agents already seeded.")
        await db.commit()
        return

    logger.info("Seeding 5 initial platform-owned agents...")

    initial_agents = [
        {
            "name": "Deep Research Agent",
            "slug": "research-agent",
            "category_slug": "research",
            "icon": "🔍",
            "short_description": "Researches user-specified topics, organizes key findings, and produces structured analytical reports.",
            "description": "The Deep Research Agent accepts complex questions and topics, organizes findings into core themes, highlights key evidence, and produces structured executive summaries with citations.",
            "pricing_type": PricingType.FREE,
            "price_per_execution": 0,
            "system_prompt": (
                "You are an expert Research Analyst. Given a user topic or query, break down the investigation into:\n"
                "1. Executive Summary\n"
                "2. Key Findings & Thematic Analysis\n"
                "3. Strategic Implications & Recommendations\n"
                "4. Cited Sources & Evidence\n"
                "Maintain objective, factual rigor throughout."
            ),
        },
        {
            "name": "Document Analysis Agent",
            "slug": "document-agent",
            "category_slug": "document-processing",
            "icon": "📄",
            "short_description": "Processes text documents, summaries, and extracts key data into structured markdown.",
            "description": "Accepts text, extracts central arguments, creates hierarchical outlines, and identifies critical clauses or data points.",
            "pricing_type": PricingType.FREE,
            "price_per_execution": 0,
            "system_prompt": (
                "You are a Document Intelligence Agent. Your goal is to process user-provided documents, extract critical facts, "
                "synthesize long-form arguments into clear points, and answer any specific questions about the text."
            ),
        },
        {
            "name": "Customer Support Agent",
            "slug": "customer-support-agent",
            "category_slug": "customer-support",
            "icon": "🎧",
            "short_description": "Answers queries from approved documentation, identifies unresolved questions, and drafts escalation notes.",
            "description": "Operates with empathy and accuracy. Evaluates user complaints or inquiries, identifies root causes, answers known solutions, and flags tickets requiring human intervention.",
            "pricing_type": PricingType.FREE,
            "price_per_execution": 0,
            "system_prompt": (
                "You are a Senior Customer Support Specialist. Address customer questions with clarity, empathy, and professional etiquette. "
                "If an issue cannot be resolved directly, provide an Escalation Summary clearly stating the customer's intent and required follow-up."
            ),
        },
        {
            "name": "Lead Research & Scoring Agent",
            "slug": "lead-research-agent",
            "category_slug": "sales-marketing",
            "icon": "🎯",
            "short_description": "Scores prospective leads against ICP criteria and generates outreach talking points.",
            "description": "Analyzes prospect company profile, business model, and pain points to calculate an Ideal Customer Profile (ICP) fit score (1-100) and draft tailored value propositions.",
            "pricing_type": PricingType.FREE,
            "price_per_execution": 0,
            "system_prompt": (
                "You are a B2B Sales Development & Lead Intelligence Agent. Evaluate the provided prospect profile, "
                "score alignment with standard B2B SaaS ICP criteria (0-100), identify top 3 pain points, and draft tailored cold email talking points."
            ),
        },
        {
            "name": "Executive Email Assistant",
            "slug": "email-assistant",
            "category_slug": "email",
            "icon": "✉️",
            "short_description": "Drafts, categorizes, summarizes incoming threads, and suggests contextual responses.",
            "description": "Streamlines inbox triage. Summarizes lengthy correspondence threads, detects tone, categorizes urgency (Urgent, Action Required, Informational), and drafts polite, concise responses.",
            "pricing_type": PricingType.FREE,
            "price_per_execution": 0,
            "system_prompt": (
                "You are an Executive Email Assistant. Analyze incoming emails to:\n"
                "1. Categorize urgency (Urgent / High / Low)\n"
                "2. Summarize key requests and action items\n"
                "3. Draft professional, polished responses ready for human review before sending."
            ),
        },
    ]

    for a_data in initial_agents:
        cat = cat_map.get(a_data["category_slug"])
        agent = Agent(
            creator_id=admin.id,
            category_id=cat.id if cat else None,
            name=a_data["name"],
            slug=a_data["slug"],
            description=a_data["description"],
            short_description=a_data["short_description"],
            icon=a_data["icon"],
            tags=["platform", a_data["category_slug"]],
            status=AgentStatus.APPROVED,
            visibility=AgentVisibility.PUBLIC,
            is_platform_owned=True,
            pricing_type=a_data["pricing_type"],
            price_per_execution=a_data["price_per_execution"],
            total_executions=42,
            average_rating=4.9,
            review_count=12,
        )
        db.add(agent)
        await db.flush()

        # Add initial approved version
        version = AgentVersion(
            agent_id=agent.id,
            version_number=1,
            system_prompt=a_data["system_prompt"],
            objective=a_data["short_description"],
            model_provider="development",
            model_name="default",
            temperature=0.7,
            max_tokens=4096,
            max_steps=10,
            max_duration_seconds=300,
            is_published=True,
        )
        db.add(version)
        await db.flush()

        agent.current_version_id = version.id

    await db.commit()
    logger.info("Database seeding complete with 5 platform agents.")
