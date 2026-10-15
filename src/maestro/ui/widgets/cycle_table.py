from textual.widgets import DataTable
from maestro.models import CycleRecord


class CycleTable(DataTable):
    def __init__(self) -> None:
        super().__init__(id="cycle-table", cursor_type="row", zebra_stripes=True)
        self.add_columns("Cycle", "Status", "File", "Duration")
        self.records: dict[int, CycleRecord] = {}

    def add_record(self, record: CycleRecord) -> None:
        self.records[record.cycle_number] = record
        key = str(record.cycle_number)
        values = (key, record.status, record.target_file, f"{record.duration_sec:.1f}s")
        try:
            self.update_cell(key, "Status", record.status)
            self.update_cell(key, "File", record.target_file)
            self.update_cell(key, "Duration", f"{record.duration_sec:.1f}s")
        except Exception:
            self.add_row(*values, key=key)

    def selected_record(self) -> CycleRecord | None:
        if self.row_count == 0:
            return None
        try:
            key = self.get_row_at(self.cursor_row)[0]
            return self.records.get(int(str(key)))
        except (IndexError, ValueError, TypeError):
            return None
