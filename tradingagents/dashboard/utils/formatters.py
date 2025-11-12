def stance_color(stance: str) -> str:
    s = (stance or "").lower()
    if s == "bull": return "#16a34a"   # green
    if s == "bear": return "#dc2626"   # red
    return "#6b7280"                   # gray

def decision_color(decision: str) -> str:
    d = (decision or "").lower()
    if d == "buy": return "#16a34a"
    if d == "sell": return "#dc2626"
    return "#6b7280"

def pct(v, nd=2):
    try:
        return f"{float(v)*100:.{nd}f}%"
    except Exception:
        return "-"