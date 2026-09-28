class NoteTech:
    def __init__(self):
        pass

    def note_ing(self, ingenieur: bool) -> int:
        return 6 if ingenieur else 0

    def note_ts(self, ts: bool) -> int:
        return 4 if ts else 0

    def note_metreur(self, metreur: bool) -> int:
        return 6 if metreur else 0

    def note_ouvrier(self, nb_ouvrier: int) -> int:
        return nb_ouvrier * 4

    def note_camion(self, camion: bool) -> int:
        return 5 if camion else 0

    def note_nacelle(self, nacelle: bool) -> int:
        return 5 if nacelle else 0

    def note_moyen_de_levage(self, moyen_de_levage: int) -> int:
        return moyen_de_levage * 5

    def note_outillage(self, outillage: int) -> int:
        return outillage * 2

    def critere1(self, ingenieur: bool, ts: bool, metreur: bool, nb_ouvrier: int) -> int:
        return (
            self.note_ing(ingenieur) +
            self.note_ts(ts) +
            self.note_metreur(metreur) +
            self.note_ouvrier(nb_ouvrier)
        )

    def critere2(self, camion: bool, nacelle: bool, moyen_levage: int, outillage: int) -> int:
        return (
            self.note_camion(camion) +
            self.note_nacelle(nacelle) +
            self.note_moyen_de_levage(moyen_levage) +
            self.note_outillage(outillage)
        )

    def critere3(self, delai_soumissionnaire: int, n_lot: int) -> float:
        if n_lot in [1, 2, 4, 5, 7, 9, 10]:
            delai_min = 60
            delai_max = 120
        elif n_lot in [3, 6, 8, 11]:
            delai_min = 45
            delai_max = 90
        else:
            return 0

        if delai_soumissionnaire < delai_min or delai_soumissionnaire > delai_max:
            return 0

        n = 7.5
        note = (delai_max * n) / delai_soumissionnaire

        if delai_soumissionnaire == delai_min:
            note = 15
        elif delai_soumissionnaire == delai_max:
            note = 7.5

        note = round(note, 2)    
        return note

    def critere4(self, delai_garantie: int) -> int:
        if delai_garantie < 12:
            return 0
        elif delai_garantie == 12:
            return 5
        elif delai_garantie <= 18:
            return 10
        else:
            return 15

    def calcule_note_tech(self, ingenieur, ts, ouvrier, metreur, camion, nacelle, moyen_de_levage, outillage, delai_execution, delai_garantie, n_lot) -> dict:
        note_1 = self.critere1(ingenieur, ts, metreur, ouvrier)
        note_2 = self.critere2(camion, nacelle, moyen_de_levage, outillage)
        note_3 = self.critere3(delai_execution, n_lot)
        note_4 = self.critere4(delai_garantie)

        note_tech = note_1 + note_2 + note_3 + note_4

        # Arrondir la note technique à 2 chiffres après la virgule
        note_tech = round(note_tech, 2)

        statut = "qualifié" if note_tech >= 60 and (note_1 != 0 and note_2 != 0 and note_3 != 0 and note_4 != 0) else "éliminé"

        return {
            'note_1': note_1,
            'note_ing': self.note_ing(ingenieur),
            'note_ts': self.note_ts(ts),
            'note_metreur': self.note_metreur(metreur),
            'note_ouvrier': self.note_ouvrier(ouvrier),
            'note_camion': self.note_camion(camion),
            'note_nacelle': self.note_nacelle(nacelle),
            'note_moyen_de_levage': self.note_moyen_de_levage(moyen_de_levage),
            'note_outillage': self.note_outillage(outillage),
            'note_2': note_2,
            'note_3': note_3,
            'note_4': note_4,
            'note_tech': note_tech,
            'statut': statut
        }
