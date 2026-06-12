# Plan integracji i wydania v1.1.0

Analiza repozytorium i komplet zmian gotowych do wgrania. Wszystko sprawdzone testem, łącznie z nowym przypadkiem obrotu o 180 stopni. Ten folder zawiera pełny, gotowy pakiet 1.1.0.

## 1. Co się zmienia, plik po pliku

- `generate_ehrs_forms.py`. Marker orientacji i identyfikacji. Zamiast jednego znaku w stałym miejscu, każdy formularz stawia jeden lity kwadrat 8 pt we własnym slocie w lewym marginesie. Pilot wyżej, lekarz niżej, dyspozytor najniżej. Słownik MARK_SLOTS, metoda `orientation_pip()` rysująca w slocie tego formularza. Wersja układu podbita na v1.1, dodane pola `orientation_pip_side_pt` oraz top-level `orientation_id` z listą wszystkich slotów.
- `omr_reader.py`. Trzy poprawki z recenzji, wykrywanie orientacji oraz rozpoznawanie formularza. `build_homography_oriented()` wybiera homografię prostą albo obróconą o 180 stopni po tym, który slot wypada na tusz. `identify_form()` liczy homografię ze wspólnych fiducjali, próbkuje wszystkie sloty w obu orientacjach i bierze maksimum, zwracając naraz orientację i formularz. `process_images_auto()` rozdziela płaski folder mieszanych skanów na strumienie. CLI dostaje `--auto`. Próg Otsu zamiast 128, try/except per plik.
- `test_omr_roundtrip.py`. Dodany przypadek skanu obróconego o 180 stopni oraz przypadek worka, czyli jeden płaski folder mieszanych skanów z neutralnymi nazwami plików, rozdzielany wyłącznie po markerze.
- `EHRS_forms_layout.json` oraz `EHRS_forms_layout_full.json`. Zregenerowane, zawierają `orientation_pip` dla każdego formularza, wersja v1.1.
- Sześć plików PDF formularzy. Zregenerowane, niosą marker.
- `README_EHRS_OMR.md` oraz `README_ehrs-omr.md`. Orientacja przeramowana z ograniczenia na cechę wykrywaną automatycznie. Cytowanie i znaczek DOI wskazują DOI koncepcyjny 20592466.
- `CITATION.cff`. Wersja 1.1.0, pole doi na koncepcyjnym 20592466, miejsce na DOI wersyjny 1.1.0.
- `CHANGELOG.md`. Nowy.

Bez zmian. `LICENSE`, `NOTICE`, zestaw pól formularzy, geometria czterech fiducjali, cała logika odczytu bąbelków.

## 2. Nowe zachowanie

- Rozpoznawanie formularza. Czytnik sam ustala, czy skan to pilot, lekarz czy dyspozytor, czytając, który slot markera jest zaznaczony. Operator może wrzucić wszystkie skany do jednego płaskiego folderu i uruchomić `--auto`, bez sortowania na podfoldery. Znika cała klasa błędów z pomyłką folderu. Dotychczasowy tryb `--root` z podfolderami oraz `--form` zostają.
- Marker orientacji. Skan obrócony do góry nogami jest wykrywany i czytany poprawnie, bez ręcznego obracania pliku. Czytnik nie obraca obrazu, tylko wybiera właściwą homografię.
- Próg dynamiczny Otsu. Skany przyciemnione lub nierówno oświetlone, na przykład zdjęcia telefonem, czytają się poprawnie tam, gdzie sztywny 128 zawodził.
- Odporność seryjna. Jeden uszkodzony lub nierozpoznany plik nie kładzie całej paczki, jest pomijany z ostrzeżeniem.

## 3. Zgodność wsteczna

Formularze wydrukowane z 1.0.0 nie mają markera. Czytnik 1.1.0 widzi układ bez `orientation_pip` i czyta je jak dotąd, zakładając orientację pionową. Stary zapas druku pozostaje użyteczny przez `--root` albo `--form`. W trybie `--auto` skan bez markera nie jest zgadywany, tylko pomijany z ostrzeżeniem, więc starych formularzy nie wrzucaj do worka, czytaj je dotychczasową ścieżką. Wszystko potwierdzone testem.

## 4. Ważne dla wdrożenia

Formularze PDF się zmieniły, bo niosą teraz marker. Żeby działała detekcja orientacji, trzeba przedrukować formularze z nowych PDF. Stare wydruki dalej czytają, ale bez zabezpieczenia na obrót o 180 stopni.

Próbne skany `EHRS_sample_scan_*.png` w repo pochodzą z 1.0.0. Opcjonalnie zregeneruj je dla spójności, uruchamiając test, który renderuje nowe formularze i sadzi odpowiedzi.

## 5. Manuskrypt

Zostaje przy 1.0.0. Sekcja Availability of data and materials cytuje DOI wersyjny 10.5281/zenodo.20592467, czyli zamrożone 1.0.0, i tak ma zostać. Po nadaniu DOI wersyjnego 1.1.0 decyzja, czy przełączyć odnośnik w manuskrypcie na nowszą wersję, należy do Ciebie. Domyślnie nie przełączamy, bo walidacja w pracy szła na formularzach 1.0.0.

## 6. Kroki wydania, do wykonania przez Ciebie

1. Wgraj pliki z tego pakietu do repozytorium, nadpisując odpowiedniki.
2. Ustaw `date-released` w `CITATION.cff` na rzeczywistą datę wydania.
3. Commit, tag `v1.1.0`, utwórz Release na GitHub.
4. Jeśli repozytorium jest spięte z Zenodo integracją GitHub, nowy DOI wersyjny 1.1.0 powstanie automatycznie. Odczytaj go z rekordu Zenodo.
5. Wstaw ten DOI wersyjny 1.1.0 w `CITATION.cff` w miejsce 10.5281/zenodo.XXXXXXXX, commit.

## 7. Co przekazujesz mi po wydaniu

DOI wersyjny 1.1.0. Wstawię go w `CITATION.cff` w miejsce placeholdera oraz, jeśli zdecydujesz, zaktualizuję odnośnik w manuskrypcie. Do tego czasu placeholder zostaje.
