# Florida Income-Based Housing Research Workflow

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run the scraper

```bash
python run_all.py
```

## Rerun only one city

```bash
python search_sources.py --city "Leesburg"
python scrape_pages.py --city "Leesburg"
python normalize_properties.py
python enrich_official_sources.py
python rent_extractor.py
python apply_requirements_extractor.py
python vacancy_estimator.py
python export_results.py
```

## Open the final Excel file

Open `housing_results.xlsx` in Excel, LibreOffice Calc, or Numbers.

## Manual verification guidance

- Start with the `Call Required` sheet in the Excel workbook.
- Use `call_script.md` to track phone calls.
- Prioritize records with higher vacancy scores and stronger confidence scores.
- Treat any `NOT FOUND` or `NEEDS CALL` fields as unresolved until confirmed directly by the property.

## Plain-English Summary

### Best options to call first
| property_name | city | program_type | phone | vacancy_likelihood_score | confidence_score |
| --- | --- | --- | --- | --- | --- |
| Lake North Apts II | Lady Lake | USDA RD 515 |  | 4 | 72 |
| Lakewood Villas | Lady Lake | USDA RD 515 | (352) 753-1006 | 3 | 94 |
| Lakewood Villas | Leesburg | Unknown | (727) 449-1182 | 3 | 94 |
| Misty Wood Apartments | Bushnell | Unknown affordable rental | (352) 793-8211 | 3 | 93 |
| Lake North Apts LTD | Lady Lake | USDA RD 515 |  | 3 | 72 |
| Wildwood Terrace | Wildwood | Unknown affordable rental | (352) 748-0013 | 3 | 71 |
| Orangewood Villas | Umatilla | Unknown | (352) 669-0009 | 3 | 64 |
| Panasoffkee Family Apartments | Lake Panasoffkee | Unknown affordable rental | (352) 793-2288 | 2 | 87 |
| Lakeview Villas LTD | Clermont | Unknown | 1 (352) 394-2896 | 2 | 84 |
| Mirror Lake Manor | Fruitland Park | USDA RD 515 | 1 352-728-4208 | 2 | 84 |

### Properties most likely to have vacancy
| property_name | city | vacancy_likelihood_score | vacancy_likelihood_reason |
| --- | --- | --- | --- |
| Lake North Apts II | Lady Lake | 4 | Source indicates units are available now. |
| Lakewood Villas | Lady Lake | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Lakewood Villas | Leesburg | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Misty Wood Apartments | Bushnell | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Lake North Apts LTD | Lady Lake | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Wildwood Terrace | Wildwood | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Orangewood Villas | Umatilla | 3 | Source indicates the property is accepting applications or has an open waitlist. |
| Panasoffkee Family Apartments | Lake Panasoffkee | 2 | No reliable online vacancy evidence located; property verification is required. |
| Lakeview Villas LTD | Clermont | 2 | No reliable online vacancy evidence located; property verification is required. |
| Mirror Lake Manor | Fruitland Park | 2 | No reliable online vacancy evidence located; property verification is required. |

### Properties most likely to be truly income-based
| property_name | city | program_type | rent_type |
| --- | --- | --- | --- |
| Lake North Apts II | Lady Lake | USDA RD 515 | max LIHTC rent |
| Lakewood Villas | Lady Lake | USDA RD 515 | max LIHTC rent |
| Lakewood Villas | Leesburg | Unknown | max LIHTC rent |
| Misty Wood Apartments | Bushnell | Unknown affordable rental | max LIHTC rent |
| Lake North Apts LTD | Lady Lake | USDA RD 515 | max LIHTC rent |
| Wildwood Terrace | Wildwood | Unknown affordable rental | max LIHTC rent |
| Orangewood Villas | Umatilla | Unknown | max LIHTC rent |
| Panasoffkee Family Apartments | Lake Panasoffkee | Unknown affordable rental | income-based |
| Mirror Lake Manor | Fruitland Park | USDA RD 515 | income-based |
| Fruitland Acres LTD | Fruitland Park | USDA RD 515 | income-based |

### Properties with exact rent published
| property_name | city | exact_published_rent_by_bedroom |
| --- | --- | --- |
| Lake North Apts II | Lady Lake | $1558; $1638; $1857; $2362; $2849 |
| Lakewood Villas | Lady Lake | $761.00 - $916.00; $828.00 - $1,014.00 |
| Lakewood Villas | Leesburg | $1558; $1638; $1857; $2362; $2849 |
| Misty Wood Apartments | Bushnell | $945; $951; $1250; $1572; $1665 |
| Lake North Apts LTD | Lady Lake | $1558; $1638; $1857; $2362; $2849 |
| Wildwood Terrace | Wildwood | $945; $951; $1250; $1572; $1665 |
| Orangewood Villas | Umatilla | $1558; $1638; $18; $1857; $2362; $2849 |
| Panasoffkee Family Apartments | Lake Panasoffkee | $48,400; $88,300; $59,500 |
| Tall Pines Villas | Eustis | $705 - $758 |
| Bushnell Garden Apartments | Bushnell | $600; $811; $700; $917; $775; $999 |

### Properties where rent requires phone/application verification
| property_name | city | rent_type |
| --- | --- | --- |
| Lakeview Villas LTD | Clermont | unknown |
| Mirror Lake Manor | Fruitland Park | income-based |
| Pendry Villas | Eustis | unknown |
| Wildwood Commons | Wildwood | fixed affordable rent |
| Panasoffkee Senior Apartments | Lake Panasoffkee | fixed affordable rent |
| Wildwood Townhomes | Wildwood | fixed affordable rent |
| Bushnell Gardens II | Bushnell | fixed affordable rent |
| Lake Sumter Reserve Apartment Homes | Lady Lake | fixed affordable rent |
| Austin Commons | Eustis | unknown |
| Windemere Villas | Leesburg | unknown |

### Properties with senior/disabled restrictions
| property_name | city | property_type |
| --- | --- | --- |
| Panasoffkee Senior Apartments | Lake Panasoffkee | Senior 62+ |

### Properties with family/general eligibility
| property_name | city | population_served |
| --- | --- | --- |
| Lake North Apts II | Lady Lake | general low-income |
| Misty Wood Apartments | Bushnell | general low-income |
| Lake North Apts LTD | Lady Lake | general low-income |
| Wildwood Terrace | Wildwood | general low-income |
| Fruitland Acres LTD | Fruitland Park | general low-income |

### Application documents most commonly required
- government-issued ID: 1
- Social Security card: 1
- proof of income: 1
- bank statements: 1
- tax returns: 1

### Important warnings
- Some properties explicitly appear to have closed waitlists.
- Many properties still require phone verification for current availability.
- Several records depend partly on third-party listings and should be verified against the property directly.

