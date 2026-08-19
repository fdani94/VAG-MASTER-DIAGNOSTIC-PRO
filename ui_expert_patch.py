def apply(MainWindow):
    def show_selected_dtc_expert(self):
        row = self.dtc_table.currentRow()
        rows = self.dtc_table.property("rows") or []
        if row < 0 or row >= len(rows):
            return
        r = rows[row]
        self.dtc_title.setText(f'{r["code"]} • {r["title"]}')
        keys = set(r.keys())
        component = r["component"] if "component" in keys else ""
        location = r["component_location"] if "component_location" in keys else ""
        test_path = r["test_path"] if "test_path" in keys else ""
        text = (
            f'DESCRIERE\n{r["description"]}\n\n'
            f'SIMPTOME\n{r["symptoms"]}\n\n'
            f'CAUZE POSIBILE\n{r["causes"]}\n\n'
            f'PIESA / SISTEM SUSPECT\n{component or "Depinde de codul motor / echipare"}\n\n'
            f'UNDE ESTE PIESA\n{location or "Poziția exactă trebuie confirmată după cod motor / platformă"}\n\n'
            f'TEST ÎN VCDS\n{test_path or "Vezi procedura specifică din Workspace VCDS"}\n\n'
            f'DIAGNOSTIC PAS CU PAS\n{r["diagnosis"]}\n\n'
            f'REPARAȚIE\n{r["repair"]}\n\n'
            f'SEVERITATE\n{r["severity"]}\n\n'
            f'STATUS\n{"VERIFICAT" if r["verified"] else "DE VERIFICAT / starter"}'
        )
        self.dtc_text.setPlainText(text)

    MainWindow.show_selected_dtc = show_selected_dtc_expert
