import os
import requests
from pathlib import Path

# Configuration
DEST_DIR = Path(r"c:\Users\Bot\Desktop\Thor\data\raw\external_nutrition")
DEST_DIR.mkdir(parents=True, exist_ok=True)

PDF_SOURCES = {
    "human_nutrition_textbook.pdf": "https://2012books.lardbucket.org/pdfs/an-introduction-to-nutrition.pdf",
    "antioxidants_in_sport_nutrition.pdf": "https://pdf.infobooks.org/ING/PDF/Migration/antioxidants-in-sport-nutrition-manfred-lamprecht.pdf",
    "sports_nutrition_toolkit.pdf": "https://pdf.infobooks.org/ING/PDF/Migration/sports-nutrition-toolkit-lian-brown-caroline-tarnowski.pdf",
    "csun_sports_nutrition_guide.pdf": "https://pdf.infobooks.org/ING/PDF/Migration/sports-nutrition-california-state-university-northridge.pdf",
    "vegetarian_vegan_athlete_guide.pdf": "https://pdf.infobooks.org/ING/PDF/Migration/vegetarian-and-vegan-diets-for-athletes-gatorade-sports-science-institute.pdf",
    "truesport_fueling_performance.pdf": "https://pdf.infobooks.org/ING/PDF/Migration/nutrition-guide-fueling-for-performance-truesport.pdf"
}

def download_pdf(name, url):
    dest = DEST_DIR / name
    print(f"Downloading {name} from {url}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully saved to {dest}")
        # Create a sidecar JSON for compatibility with the existing pipeline
        metadata = {
            "source": "external_nutrition",
            "title": name.replace("_", " ").replace(".pdf", "").title(),
            "url": url,
            "pdf_path": name,
            "fetched_at": "2026-04-17T12:00:00Z"
        }
        with open(dest.with_suffix(".json"), 'w') as f:
            import json
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    for name, url in PDF_SOURCES.items():
        download_pdf(name, url)
