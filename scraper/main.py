from .crawler import LeganetCrawler

CATEGORIES = {
    "Droit civil": "https://www.leganet.cd/Legislation/Tables/droit_civil.htm",
    "Droit économique": "https://www.leganet.cd/Legislation/Tables/droit_economique.htm",
    "Droit judiciaire": "https://www.leganet.cd/Legislation/Tables/droit_judiciaire.htm",
    "Droit pénal": "https://www.leganet.cd/Legislation/Tables/droit_penal.htm",
    "Droit public": "https://www.leganet.cd/Legislation/Tables/droit_public.htm",
    "Droit social": "https://www.leganet.cd/Legislation/Tables/droit_social.htm",
    "Droit fiscal": "https://www.leganet.cd/Legislation/Tables/droitfiscal.htm",
    "Provinces": "https://www.leganet.cd/Legislation/Tables/provinces.htm"
}

def main():
    crawler = LeganetCrawler()
    
    # For a full run, iterate through all categories.
    # For testing, we could just do one.
    for name, url in CATEGORIES.items():
        try:
            crawler.crawl_category(name, url)
        except Exception as e:
            print(f"Error crawling category {name}: {e}")

if __name__ == "__main__":
    main()
