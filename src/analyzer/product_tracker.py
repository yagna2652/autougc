"""
Product Tracker - Consolidates and tracks product appearances across scenes.

Aggregates product data from scene analysis to provide:
1. Product identification and naming
2. Total screen time calculation
3. Demo moment tracking
4. Product visibility timeline
5. Key features highlighted
"""

from src.models.blueprint import (
    ProductAppearance,
    ProductInfo,
    ProductTracking,
    Scene,
    SceneBreakdown,
)


class ProductTracker:
    """
    Tracks and consolidates product appearances across all scenes.
    """

    def __init__(self):
        """Initialize the product tracker."""
        pass

    def track_products(
        self,
        scene_breakdown: SceneBreakdown,
        total_duration: float,
    ) -> ProductTracking:
        """
        Consolidate product tracking from scene breakdown.

        Args:
            scene_breakdown: Complete scene breakdown with product appearances
            total_duration: Total video duration

        Returns:
            ProductTracking with consolidated product information
        """
        # Collect all product appearances
        all_appearances: list[tuple[Scene, ProductAppearance]] = []

        for scene in scene_breakdown.scenes:
            for appearance in scene.product_appearances:
                all_appearances.append((scene, appearance))

        if not all_appearances:
            return ProductTracking(
                products=[],
                primary_product=None,
                total_product_screen_time=0.0,
                product_to_content_ratio=0.0,
            )

        # Group appearances by product name
        product_groups: dict[str, list[tuple[Scene, ProductAppearance]]] = {}

        for scene, appearance in all_appearances:
            # Normalize product name for grouping
            name = self._normalize_product_name(appearance.product_name)
            if name not in product_groups:
                product_groups[name] = []
            product_groups[name].append((scene, appearance))

        # Create ProductInfo for each product
        products = []
        for name, appearances in product_groups.items():
            product_info = self._create_product_info(name, appearances)
            products.append(product_info)

        # Sort by screen time (most visible first)
        products.sort(key=lambda p: p.total_screen_time, reverse=True)

        # Primary product is the one with most screen time
        primary_product = products[0] if products else None

        # Calculate totals
        total_screen_time = sum(p.total_screen_time for p in products)
        product_ratio = total_screen_time / total_duration if total_duration > 0 else 0

        return ProductTracking(
            products=products,
            primary_product=primary_product,
            total_product_screen_time=round(total_screen_time, 2),
            product_to_content_ratio=round(product_ratio, 3),
        )

    def _normalize_product_name(self, name: str) -> str:
        """
        Normalize product name for grouping similar references.
        """
        if not name:
            return "unknown_product"

        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove common filler words
        filler_words = ["the", "a", "an", "this", "that", "some"]
        words = normalized.split()
        words = [w for w in words if w not in filler_words]

        return " ".join(words) if words else "unknown_product"

    def _create_product_info(
        self,
        name: str,
        appearances: list[tuple[Scene, ProductAppearance]],
    ) -> ProductInfo:
        """
        Create ProductInfo from grouped appearances.
        """
        # Calculate total screen time
        total_time = sum(app.duration for _, app in appearances)

        # Find first appearance
        first_appearance = min(app.timestamp for _, app in appearances)

        # Find demo moments
        demo_moments = [app.timestamp for _, app in appearances if app.is_demo]

        # Extract key features from descriptions
        features = self._extract_features(appearances)

        # Try to identify brand from product name
        brand = self._identify_brand(name, appearances)

        # Determine category
        category = self._identify_category(name, appearances)

        return ProductInfo(
            name=name.title(),
            brand=brand,
            category=category,
            total_screen_time=round(total_time, 2),
            first_appearance=round(first_appearance, 2),
            demo_moments=demo_moments,
            key_features_shown=features,
            appearance_count=len(appearances),
        )

    def _extract_features(
        self,
        appearances: list[tuple[Scene, ProductAppearance]],
    ) -> list[str]:
        """
        Extract key product features from appearance descriptions.
        """
        features = set()

        for scene, appearance in appearances:
            # Extract from appearance description
            if appearance.description:
                # Look for feature-indicating phrases
                desc_lower = appearance.description.lower()

                feature_indicators = [
                    "showing",
                    "demonstrating",
                    "highlighting",
                    "featuring",
                    "displays",
                    "reveals",
                ]

                for indicator in feature_indicators:
                    if indicator in desc_lower:
                        # Extract phrase after indicator
                        parts = desc_lower.split(indicator)
                        if len(parts) > 1:
                            feature = parts[1].strip()[:50]  # Limit length
                            if feature:
                                features.add(feature.strip(",.!"))

            # Extract from interaction type
            if appearance.interaction and appearance.interaction != "none":
                interaction = appearance.interaction.lower()
                if interaction not in ["holding", "showing", "none"]:
                    features.add(f"can be {interaction}")

            # Check for demo context
            if appearance.is_demo:
                features.add("product demonstration")

        return list(features)[:10]  # Limit to 10 features

    def _identify_brand(
        self,
        name: str,
        appearances: list[tuple[Scene, ProductAppearance]],
    ) -> str:
        """
        Try to identify the brand from product name and context.
        """
        # Check if name contains common brand indicators
        name_words = name.lower().split()

        # First word is often the brand
        if len(name_words) > 1:
            potential_brand = name_words[0]
            # Filter out generic words
            generic_words = {
                "product",
                "item",
                "bottle",
                "box",
                "package",
                "small",
                "large",
                "medium",
                "new",
                "old",
            }
            if potential_brand not in generic_words:
                return potential_brand.title()

        # Check appearance descriptions for brand mentions
        for _, appearance in appearances:
            if appearance.product_name:
                words = appearance.product_name.split()
                if words:
                    return words[0].title()

        return ""

    def _identify_category(
        self,
        name: str,
        appearances: list[tuple[Scene, ProductAppearance]],
    ) -> str:
        """
        Try to identify the product category.
        """
        name_lower = name.lower()

        # Category keywords mapping
        category_keywords = {
            "supplement": ["gummies", "vitamins", "supplement", "pills", "capsules"],
            "skincare": [
                "serum",
                "cream",
                "moisturizer",
                "cleanser",
                "lotion",
                "skincare",
            ],
            "makeup": [
                "lipstick",
                "mascara",
                "foundation",
                "concealer",
                "makeup",
                "palette",
            ],
            "haircare": ["shampoo", "conditioner", "hair", "styling"],
            "food": ["snack", "drink", "food", "bar", "protein", "meal"],
            "technology": ["phone", "laptop", "device", "gadget", "tech", "app"],
            "fashion": ["shirt", "pants", "dress", "shoes", "clothing", "outfit"],
            "fitness": ["workout", "exercise", "gym", "fitness", "equipment"],
            "home": ["decor", "furniture", "kitchen", "home", "appliance"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        # Check descriptions
        for _, appearance in appearances:
            desc_lower = (appearance.description or "").lower()
            for category, keywords in category_keywords.items():
                for keyword in keywords:
                    if keyword in desc_lower:
                        return category

        return "general"


def create_product_timeline(
    product_tracking: ProductTracking,
    total_duration: float,
    resolution: float = 1.0,
) -> list[dict]:
    """
    Create a timeline of product visibility.

    Args:
        product_tracking: Consolidated product tracking data
        total_duration: Total video duration
        resolution: Time resolution in seconds

    Returns:
        List of time points with product visibility info
    """
    timeline = []

    time_point = 0.0
    while time_point < total_duration:
        visible_products = []

        for product in product_tracking.products:
            # Check if product is visible at this time
            # This is a simplified check - in reality you'd need
            # the original appearance data with start/end times
            if product.first_appearance <= time_point:
                visible_products.append(product.name)

        timeline.append(
            {
                "timestamp": round(time_point, 1),
                "products_visible": visible_products,
                "is_demo_moment": any(
                    abs(dm - time_point) < resolution
                    for p in product_tracking.products
                    for dm in p.demo_moments
                ),
            }
        )

        time_point += resolution

    return timeline


def calculate_product_metrics(
    product_tracking: ProductTracking,
    total_duration: float,
) -> dict:
    """
    Calculate summary metrics for product placements.

    Args:
        product_tracking: Consolidated product tracking data
        total_duration: Total video duration

    Returns:
        Dictionary of product placement metrics
    """
    if not product_tracking.products:
        return {
            "has_product": False,
            "product_count": 0,
            "avg_screen_time": 0,
            "demo_count": 0,
            "first_product_appearance": 0,
            "product_density": 0,
        }

    primary = product_tracking.primary_product

    return {
        "has_product": True,
        "product_count": len(product_tracking.products),
        "primary_product": primary.name if primary else "Unknown",
        "primary_brand": primary.brand if primary else "",
        "primary_category": primary.category if primary else "",
        "total_screen_time": product_tracking.total_product_screen_time,
        "avg_screen_time": round(
            product_tracking.total_product_screen_time / len(product_tracking.products),
            2,
        ),
        "product_to_content_ratio": product_tracking.product_to_content_ratio,
        "demo_count": sum(len(p.demo_moments) for p in product_tracking.products),
        "first_product_appearance": min(
            p.first_appearance for p in product_tracking.products
        ),
        "total_appearances": sum(p.appearance_count for p in product_tracking.products),
        "product_density": round(
            sum(p.appearance_count for p in product_tracking.products)
            / total_duration
            * 60,
            1,
        )
        if total_duration > 0
        else 0,  # Appearances per minute
    }
