from OCR import ocr_event_image
from dateparser.search import search_dates
import re
from datetime import datetime, timedelta
import dateparser

from dateparser.search import search_dates
from datetime import datetime, timedelta
import dateparser
import re

def parse_event_spec(text: str, default_duration_minutes=60):
    # 0) Normalize & collapse lines into a flat string
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    flat  = " ".join(lines)

    # 1) Title = first two lines
    title = " — ".join(lines[:2]) if len(lines)>=2 else lines[0]

    now = datetime.now()

    # 2) Month-Day detection by token search
    tokens = re.split(r'\s+', flat)
    # months mapping
    MONTHS = {m: m for m in [
        "JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"
    ]}
    month_idx = next((i for i,t in enumerate(tokens)
                      if t.upper() in MONTHS), None)

    if month_idx is not None:
        # search backwards for a numeric day
        day = None
        for j in range(month_idx-1, -1, -1):
            if tokens[j].isdigit():
                day = int(tokens[j]); break
        if day:
            mon = tokens[month_idx].upper()
            # parse with dateparser, forcing future
            dt = dateparser.parse(f"{day} {mon}",
                                  settings={"PREFER_DATES_FROM":"future"})
            base_date = dt if dt else now
        else:
            base_date = now
    else:
        # 3) fallback to ordinal-day parsing (e.g. "24TH")
        m_ord = re.search(r'\b(\d{1,2})(?:ST|ND|RD|TH)\b',
                          flat, re.IGNORECASE)
        if m_ord:
            day = int(m_ord.group(1))
            try_date = now.replace(day=day)
            if try_date.date() < now.date():
                # bump month
                y,m = (now.year+1,1) if now.month==12 else (now.year,now.month+1)
                try_date = try_date.replace(year=y, month=m)
            base_date = try_date
        else:
            # 4) ultimate fallback to search_dates
            found = search_dates(flat, settings={"PREFER_DATES_FROM":"future"}) or []
            base_date = found[0][1] if found else now

    # 5) Time detection (HH:MM or H AM/PM)
    time_strs = re.findall(r'\b\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b',
                           flat, re.IGNORECASE)
    times = []
    for ts in time_strs:
        dt = dateparser.parse(ts)
        if dt: times.append(dt.time())
    if len(times)>=2:
        start, end = times[0], times[1]
    elif len(times)==1:
        start = times[0]
        end   = (datetime.combine(base_date, start)
                 + timedelta(minutes=default_duration_minutes)).time()
    else:
        # defaults if nothing found
        start = datetime.strptime("09:00","%H:%M").time()
        end   = (datetime.combine(base_date, start)
                 + timedelta(minutes=default_duration_minutes)).time()

    # 6) Location: look for "<text>, ST"
    m_loc = re.search(r'([A-Za-z0-9 .\-]+,\s*[A-Za-z]{2}\b)', flat)
    location = m_loc.group(1).strip() if m_loc else ""

    # 7) Description: strip out title/date/time/location bits
    desc = flat
    # remove the month-day phrase if we used it
    if month_idx is not None and day:
        phrase = tokens[month_idx-1] + " " + tokens[month_idx]
        desc = re.sub(re.escape(phrase), "", desc, flags=re.IGNORECASE)
    # remove any standalone ordinals
    desc = re.sub(r'\b\d{1,2}(?:ST|ND|RD|TH)\b', "", desc, flags=re.IGNORECASE)
    # remove all time substrings
    for ts in time_strs:
        desc = re.sub(re.escape(ts), "", desc, flags=re.IGNORECASE)
    # remove location
    if location:
        desc = desc.replace(location, "")
    description = " ".join(desc.split()).strip()

    # 8) Category
    if re.search(r'\bvolunteer|festival|community\b', flat, re.IGNORECASE):
        category = "Community"
    elif re.search(r'\bmeeting|call|appointment\b', flat, re.IGNORECASE):
        category = "Meeting"
    else:
        category = "Personal"

    return {
        "title"      : title,
        "date"       : base_date.date().isoformat(),
        "start_time" : start.strftime("%H:%M"),
        "end_time"   : end.strftime("%H:%M"),
        "location"   : location,
        "description": description,
        "category"   : category
    }


if __name__ == "__main__":
    raw_text = ocr_event_image("event.jpeg")
    print("OCR’d text:\n", raw_text, "\n")
    spec = parse_event_spec(raw_text)
    import json
    print("Event spec:\n", json.dumps(spec, indent=2))
