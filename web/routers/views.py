from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web.data_loader import load_data, get_dashboard_stats

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def get_source_color(source: str) -> str:
    colors = {
        "sreality": "#3b82f6",
        "bezrealitky": "#10b981",
        "annonce": "#f59e0b",
        "bazos": "#ef4444",
        "realityidnes": "#8b5cf6",
        "hyperreality": "#ec4899",
        "realcity": "#06b6d4",
    }
    return colors.get(source, "#6b7280")


def get_source_label(source: str) -> str:
    labels = {
        "sreality": "Sreality",
        "bezrealitky": "Bezrealitky",
        "annonce": "Annonce",
        "bazos": "Bazos",
        "realityidnes": "Reality iDNES",
        "hyperreality": "HyperReality",
        "realcity": "Realcity",
    }
    return labels.get(source, source)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = load_data()
    stats = get_dashboard_stats(data)
    opportunities = data.get("opportunities", [])[:5]
    listings = data.get("listings", [])

    source_counts = {}
    for l in listings:
        src = l.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    source_data = [
        {"name": get_source_label(k), "value": v, "color": get_source_color(k)}
        for k, v in sorted(source_counts.items(), key=lambda x: -x[1])
    ]

    condition_counts = {}
    for l in listings:
        cond = l.get("condition") or "neuvedeno"
        condition_counts[cond] = condition_counts.get(cond, 0) + 1

    location_counts = {}
    for l in listings:
        loc = l.get("location", "neuvedeno")
        for known_loc in ["cheb", "karlovy", "sokolov", "mariánské"]:
            if known_loc in loc.lower():
                location_counts[known_loc.title()] = location_counts.get(known_loc.title(), 0) + 1
                break
        else:
            location_counts["Ostatní"] = location_counts.get("Ostatní", 0) + 1

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "opportunities": opportunities,
            "source_data": source_data,
            "condition_counts": condition_counts,
            "location_counts": location_counts,
            "listings_count": len(listings),
        },
    )


@router.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request, source: str = "", location: str = "", condition: str = ""):
    data = load_data()
    listings = data.get("listings", [])

    if source:
        listings = [l for l in listings if l.get("source") == source]
    if location:
        listings = [l for l in listings if location.lower() in (l.get("location") or "").lower()]
    if condition:
        listings = [l for l in listings if l.get("condition") == condition]

    return templates.TemplateResponse(
        "listings.html",
        {
            "request": request,
            "listings": listings,
            "source": source,
            "location": location,
            "condition": condition,
        },
    )


@router.get("/opportunities", response_class=HTMLResponse)
async def opportunities_page(request: Request):
    data = load_data()
    opportunities = data.get("opportunities", [])
    return templates.TemplateResponse(
        "opportunity.html",
        {"request": request, "opportunities": opportunities},
    )


@router.get("/detail/{listing_id}", response_class=HTMLResponse)
async def detail_page(request: Request, listing_id: int):
    data = load_data()
    listing = None
    for l in data.get("listings", []):
        if l.get("id") == listing_id:
            listing = l
            break

    if not listing:
        return templates.TemplateResponse(
            "detail.html",
            {"request": request, "listing": None},
        )

    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "listing": listing},
    )


@router.get("/api/data")
async def api_data():
    return load_data()


@router.get("/api/stats")
async def api_stats():
    data = load_data()
    return get_dashboard_stats(data)
