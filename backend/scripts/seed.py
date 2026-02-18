import asyncio
import sys
from pathlib import Path

# Allow imports from backend/app
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import SessionLocal
from app.models import Product

PRODUCTS = [
    # Jackets
    {
        "name": "Summit Pro Rain Jacket",
        "description": "Lightweight waterproof jacket with Gore-Tex membrane, sealed seams, and adjustable hood. Ideal for heavy rain and wind.",
        "price": 74.99,
        "category": "jackets",
        "brand": "TrailForce",
        "stock": 35,
    },
    {
        "name": "Alpine Down Puffer Jacket",
        "description": "800-fill goose down insulation with water-resistant shell. Packable into its own pocket. Great for cold conditions below freezing.",
        "price": 129.99,
        "category": "jackets",
        "brand": "PeakGear",
        "stock": 20,
    },
    {
        "name": "Fleece Midlayer Hoodie",
        "description": "Polartec 200-weight fleece with kangaroo pocket and thumb loops. Versatile midlayer for cool-weather hikes.",
        "price": 49.99,
        "category": "jackets",
        "brand": "TrailForce",
        "stock": 50,
    },
    # Footwear
    {
        "name": "TrailMaster Waterproof Hiking Boots",
        "description": "Full-grain leather upper with Gore-Tex lining and Vibram outsole. Ankle support and lugged tread for technical terrain.",
        "price": 89.99,
        "category": "footwear",
        "brand": "TrailMaster",
        "stock": 18,
    },
    {
        "name": "Speedhike Trail Runner",
        "description": "Lightweight trail running shoe with rock plate, breathable mesh upper, and aggressive grip outsole. 8oz per shoe.",
        "price": 64.99,
        "category": "footwear",
        "brand": "SwiftStep",
        "stock": 30,
    },
    {
        "name": "Camp Moccasin",
        "description": "Packable camp shoe with EVA foam sole. Slip on after a long day on the trail. Weighs only 4oz per pair.",
        "price": 24.99,
        "category": "footwear",
        "brand": "RestStep",
        "stock": 60,
    },
    # Sleeping
    {
        "name": "UltraLight 20F Sleeping Bag",
        "description": "800-fill down sleeping bag rated to 20°F. Mummy cut with draft collar and water-resistant shell. 1.8 lbs.",
        "price": 149.99,
        "category": "sleeping",
        "brand": "PeakGear",
        "stock": 15,
    },
    {
        "name": "3-Season Sleeping Pad",
        "description": "Self-inflating foam pad with R-value of 4.2. Comfortable and packable for 3-season backpacking.",
        "price": 59.99,
        "category": "sleeping",
        "brand": "RestCamp",
        "stock": 25,
    },
    {
        "name": "Hammock Camping Kit",
        "description": "Lightweight nylon hammock with integrated bug net and rain tarp. Sets up in under 5 minutes. Holds up to 300 lbs.",
        "price": 79.99,
        "category": "sleeping",
        "brand": "TreeSleep",
        "stock": 22,
    },
    # Packs
    {
        "name": "Ridgeline 45L Backpack",
        "description": "Top-loading pack with aluminum stay frame, hip belt, and hydration sleeve. Rain cover included. Fits torso 16–20 inches.",
        "price": 119.99,
        "category": "packs",
        "brand": "TrailForce",
        "stock": 12,
    },
    {
        "name": "Summit Daypack 20L",
        "description": "Minimalist daypack with padded laptop sleeve, trekking pole loops, and mesh back panel for airflow.",
        "price": 44.99,
        "category": "packs",
        "brand": "SwiftStep",
        "stock": 40,
    },
    {
        "name": "Ultralight Fanny Pack 5L",
        "description": "Hip-mounted 5L pack for fast-and-light day hikes. Two zippered pockets and a phone window. 4oz.",
        "price": 19.99,
        "category": "packs",
        "brand": "SwiftStep",
        "stock": 55,
    },
    # Navigation & Lighting
    {
        "name": "Black Diamond Spot 400 Headlamp",
        "description": "400-lumen waterproof headlamp with red night-vision mode, proximity and distance beams. IPX8 rated.",
        "price": 39.99,
        "category": "lighting",
        "brand": "Black Diamond",
        "stock": 45,
    },
    {
        "name": "Solar Lantern & Charger",
        "description": "Collapsible solar lantern with 1000mAh battery. Charges via USB or 6 hours of sunlight. 3 brightness modes.",
        "price": 29.99,
        "category": "lighting",
        "brand": "SunForce",
        "stock": 30,
    },
    # Hydration & Food
    {
        "name": "Sawyer Squeeze Water Filter",
        "description": "0.1-micron hollow fiber filter removes 99.9999% of bacteria and protozoa. Fits standard water bottles. Lifetime warranty.",
        "price": 34.99,
        "category": "hydration",
        "brand": "Sawyer",
        "stock": 50,
    },
    {
        "name": "Insulated 32oz Titanium Bottle",
        "description": "Double-wall vacuum-insulated titanium bottle. Keeps drinks cold 24h, hot 12h. Compatible with Sawyer filter.",
        "price": 44.99,
        "category": "hydration",
        "brand": "PeakGear",
        "stock": 35,
    },
    {
        "name": "Backpacking Stove & Pot Set",
        "description": "Canister stove with 1L hard-anodized aluminum pot, lid, and folding handle. Boils 1L in 3.5 minutes. 12oz total.",
        "price": 54.99,
        "category": "cooking",
        "brand": "TrailChef",
        "stock": 20,
    },
    # Safety & Tools
    {
        "name": "Trekking Poles (Pair)",
        "description": "Adjustable aluminum poles with cork grips, carbide tips, and snow baskets. Collapsible to 24 inches. 18oz per pair.",
        "price": 49.99,
        "category": "accessories",
        "brand": "TrailMaster",
        "stock": 28,
    },
    {
        "name": "10-in-1 Survival Multitool",
        "description": "Stainless steel multitool with knife, saw, fire starter, compass, whistle, and paracord. Fits on a keychain.",
        "price": 17.99,
        "category": "accessories",
        "brand": "SurviveAll",
        "stock": 70,
    },
    {
        "name": "First Aid Kit — Trail Edition",
        "description": "48-piece wilderness first aid kit in a waterproof roll pouch. Includes blister treatment, SAM splint, and emergency blanket.",
        "price": 27.99,
        "category": "safety",
        "brand": "MedReady",
        "stock": 40,
    },
]


async def seed():
    async with SessionLocal() as db:
        # Skip if already seeded
        result = await db.execute(select(Product))
        if result.scalars().first():
            print("Database already seeded, skipping.")
            return

        products = [Product(**p) for p in PRODUCTS]
        db.add_all(products)
        await db.commit()
        print(f"Seeded {len(products)} products.")


if __name__ == "__main__":
    asyncio.run(seed())
