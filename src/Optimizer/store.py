"""Append-only historie pokusu + drzeni best_config_id (TESTING-OPTIMIZATION §5.4).

VariantStore: historie se nikdy neprepisuje, rollback = prepnuti pointeru
best_config_id (nemenne varianty, O(1), nemuze selhat castecnym prepisem).
Kazdy rollback se loguje jako zaznam s duvodem. Pouze stdlib.
"""

import json
import os


class VariantStore:
    """Uloziste historie kampane nad adresarem `out_dir`.

    Soubory: history.jsonl (append-only), best.json (pointer + statistika).
    """

    def __init__(self, out_dir):
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.history_path = os.path.join(out_dir, "history.jsonl")
        self.best_path = os.path.join(out_dir, "best.json")
        self.records = []
        self.best_config_id = None
        self.best_stats = None
        if os.path.exists(self.history_path):
            with open(self.history_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self.records.append(json.loads(line))
        if os.path.exists(self.best_path):
            with open(self.best_path, "r", encoding="utf-8") as fh:
                best_doc = json.load(fh)
            self.best_config_id = best_doc.get("best_config_id")
            self.best_stats = best_doc.get("stats")

    def append(self, record):
        """Prida zaznam pokusu (vcetne rollbacku) na konec historie."""
        self.records.append(record)
        with open(self.history_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def set_best(self, config, stats):
        """Atomicky prepne pointer best (zapis noveho best.json pres tmp)."""
        self.best_config_id = config["config_id"]
        self.best_stats = stats
        doc = {
            "best_config_id": config["config_id"],
            "config": config,
            "stats": stats,
        }
        tmp = self.best_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.best_path)

    def log_rollback(self, kept_config_id, rejected_config_id, reason):
        """Auditni zaznam: pointer zustava na kept (odmitnuta vetev)."""
        self.append({
            "event": "rollback",
            "kept_config_id": kept_config_id,
            "rejected_config_id": rejected_config_id,
            "reason": reason,
        })

    @property
    def attempts(self):
        return [r for r in self.records if r.get("event", "attempt") == "attempt"]

    def counts(self):
        accepted = sum(1 for r in self.attempts
                       if (r.get("decision") or {}).get("accept") is True)
        return {"tested": len(self.attempts), "accepted": accepted,
                "rejected": len(self.attempts) - accepted}
