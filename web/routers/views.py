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


def get_base_context() -> dict:
    data = load_data()
    stats = get_dashboard_stats(data)
    return {"stats": stats, "data": data}


def render(request: Request, name: str, context: dict | None = None):
    ctx = get_base_context()
    if context:
        ctx.update(context)
    return templates.TemplateResponse(request, name, ctx)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = load_data()
    listings = data.get("listings", [])
    opportunities = data.get("opportunities", [])[:5]

    source_counts = {}
    for l in listings:
        src = l.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    source_labels = []
    source_values = []
    source_colors = []
    for k, v in sorted(source_counts.items(), key=lambda x: -x[1]):
        source_labels.append(get_source_label(k))
        source_values.append(v)
        source_colors.append(get_source_color(k))

    cond_labels = []
    cond_values = []
    for l in listings:
        cond = l.get("condition") or "neuvedeno"
        if cond in cond_labels:
            cond_values[cond_labels.index(cond)] += 1
        else:
            cond_labels.append(cond)
            cond_values.append(1)

    loc_labels = []
    loc_values = []
    for l in listings:
        loc = l.get("location", "neuvedeno")
        matched = False
        for known_loc in ["cheb", "karlovy", "sokolov", "mariánské"]:
            if known_loc in loc.lower():
                label = known_loc.title()
                if label in loc_labels:
                    loc_values[loc_labels.index(label)] += 1
                else:
                    loc_labels.append(label)
                    loc_values.append(1)
                matched = True
                break
        if not matched:
            if "Ostatní" in loc_labels:
                loc_values[loc_labels.index("Ostatní")] += 1
            else:
                loc_labels.append("Ostatní")
                loc_values.append(1)

    return render(request, "dashboard.html", {
        "opportunities": opportunities,
        "source_labels": source_labels,
        "source_values": source_values,
        "source_colors": source_colors,
        "cond_labels": cond_labels,
        "cond_values": cond_values,
        "loc_labels": loc_labels,
        "loc_values": loc_values,
    })


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

    return render(request, "listings.html", {
        "listings": listings, "source": source, "location": location, "condition": condition,
    })


@router.get("/opportunities", response_class=HTMLResponse)
async def opportunities_page(request: Request):
    data = load_data()
    opportunities = data.get("opportunities", [])
    return render(request, "opportunity.html", {"opportunities": opportunities})


@router.get("/detail/{listing_id}", response_class=HTMLResponse)
async def detail_page(request: Request, listing_id: int):
    data = load_data()
    listing = None
    for l in data.get("listings", []):
        if l.get("id") == listing_id:
            listing = l
            break

    return render(request, "detail.html", {"listing": listing})


@router.get("/api/data")
async def api_data():
    return load_data()


@router.get("/api/stats")
async def api_stats():
    return get_dashboard_stats(load_data())
