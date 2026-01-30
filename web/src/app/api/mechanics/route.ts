import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

interface ProductContext {
  type?: string;
  interactions?: string[];
  tactileFeatures?: string[];
  soundFeatures?: string[];
  sizeDescription?: string;
  highlightFeature?: string;
  customInstructions?: string;
}

interface MechanicsRequest {
  blueprint: Record<string, unknown>;
  basePrompt?: string;
  productCategory?: string;
  productContext?: ProductContext;
  targetDuration?: number;
  energyLevel?: string;
}

interface MechanicsFromStyleRequest {
  hookStyle?: string;
  bodyFramework?: string;
  ctaStyle?: string;
  productCategory?: string;
  productContext?: ProductContext;
  duration?: number;
  basePrompt?: string;
  energyLevel?: string;
}

interface EnhancePromptRequest {
  originalPrompt: string;
  blueprint: Record<string, unknown>;
  productCategory?: string;
  productContext?: ProductContext;
  targetDuration?: number;
}

/**
 * Convert camelCase product context to snake_case for Python API
 */
function convertProductContext(ctx?: ProductContext) {
  if (!ctx) return null;
  return {
    type: ctx.type || "",
    interactions: ctx.interactions || [],
    tactile_features: ctx.tactileFeatures || [],
    sound_features: ctx.soundFeatures || [],
    size_description: ctx.sizeDescription || "",
    highlight_feature: ctx.highlightFeature || "",
    custom_instructions: ctx.customInstructions || "",
  };
}

/**
 * POST /api/mechanics
 *
 * Proxies requests to the Python mechanics API.
 * Supports three operations via the `operation` query param:
 * - generate: Generate mechanics from blueprint
 * - from-style: Generate from style parameters
 * - enhance: Enhance an existing prompt
 */
export async function POST(request: NextRequest) {
  try {
    const operation =
      request.nextUrl.searchParams.get("operation") || "generate";

    let endpoint: string;
    let body: unknown;

    const requestBody = await request.json();

    switch (operation) {
      case "generate": {
        endpoint = `${PYTHON_API_URL}/api/v1/mechanics/generate`;
        const genRequest = requestBody as MechanicsRequest;
        body = {
          blueprint: genRequest.blueprint,
          base_prompt: genRequest.basePrompt || "",
          product_category: genRequest.productCategory || null,
          product_context: convertProductContext(genRequest.productContext),
          target_duration: genRequest.targetDuration || 8.0,
          energy_level: genRequest.energyLevel || "medium",
          include_realism_preamble: true,
        };
        break;
      }

      case "from-style": {
        endpoint = `${PYTHON_API_URL}/api/v1/mechanics/from-style`;
        const styleRequest = requestBody as MechanicsFromStyleRequest;
        body = {
          hook_style: styleRequest.hookStyle || "casual_share",
          body_framework: styleRequest.bodyFramework || "demonstration",
          cta_style: styleRequest.ctaStyle || "soft_recommendation",
          product_category: styleRequest.productCategory || "general",
          product_context: convertProductContext(styleRequest.productContext),
          duration: styleRequest.duration || 8.0,
          base_prompt: styleRequest.basePrompt || "",
          energy_level: styleRequest.energyLevel || "medium",
        };
        break;
      }

      case "enhance": {
        endpoint = `${PYTHON_API_URL}/api/v1/mechanics/enhance`;
        const enhanceRequest = requestBody as EnhancePromptRequest;
        body = {
          original_prompt: enhanceRequest.originalPrompt,
          blueprint: enhanceRequest.blueprint,
          product_category: enhanceRequest.productCategory || null,
          product_context: convertProductContext(enhanceRequest.productContext),
          target_duration: enhanceRequest.targetDuration || 8.0,
        };
        break;
      }

      default:
        return NextResponse.json(
          {
            error: `Invalid operation: ${operation}`,
            validOperations: ["generate", "from-style", "enhance"],
          },
          { status: 400 },
        );
    }

    // Call Python API
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        {
          error: "Mechanics generation failed",
          details: errorData,
        },
        { status: response.status },
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: true,
      mechanicsPrompt: data.mechanics_prompt,
      timelineData: data.timeline_data || null,
      config: data.config,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error occurred";

    // Check if it's a connection error
    if (message.includes("ECONNREFUSED")) {
      return NextResponse.json(
        {
          error: "Python API not available",
          hint: "Make sure the Python API server is running (python -m api.server)",
        },
        { status: 503 },
      );
    }

    return NextResponse.json(
      {
        error: message,
      },
      { status: 500 },
    );
  }
}

/**
 * GET /api/mechanics
 *
 * Returns available templates and configuration options.
 */
export async function GET() {
  try {
    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/mechanics/templates`,
    );

    if (!response.ok) {
      throw new Error("Failed to fetch templates");
    }

    const templates = await response.json();

    return NextResponse.json({
      status: "ok",
      templates,
    });
  } catch (error) {
    // Return hardcoded templates as fallback
    return NextResponse.json({
      status: "ok",
      source: "fallback",
      templates: {
        hookStyles: [
          {
            name: "product_reveal",
            description: "Product rises into frame with excited reveal",
          },
          {
            name: "pov_storytelling",
            description: "POV style hook with direct camera address",
          },
          {
            name: "curiosity_hook",
            description: "Creates curiosity with skeptical-to-surprised transition",
          },
          {
            name: "casual_share",
            description: "Casual, friend-sharing-discovery style hook",
          },
        ],
        bodyFrameworks: [
          {
            name: "demonstration",
            description: "Active product demonstration",
          },
          {
            name: "testimonial",
            description: "Personal experience sharing",
          },
          {
            name: "education",
            description: "Teaching/explaining content",
          },
          {
            name: "comparison",
            description: "Before/after or product comparison",
          },
        ],
        ctaStyles: [
          {
            name: "soft_recommendation",
            description: "Gentle, friendly recommendation",
          },
          {
            name: "urgent_action",
            description: "Energetic call to action",
          },
          {
            name: "curious_tease",
            description: "Leaves viewer curious, soft close",
          },
        ],
        productCategories: [
          "skincare",
          "supplement",
          "tech",
          "food",
          "fashion",
          "general",
        ],
      },
    });
  }
}
