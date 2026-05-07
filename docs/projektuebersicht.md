# Projektuebersicht

Dieses Dokument sammelt die projektrelevanten Inhalte in komprimierter Form, damit README und technische Doku getrennt bleiben.

## Einordnung

Dieses Repository ist ein Unterrepo von `DIY Garage Cut`.

Es enthält die Fusion-360-bezogenen Bausteine für:

- Modellmetadaten
- Fertigungshinweise
- Bekantung und Oberflächenlogik
- CSV-Export für externe Zuschnittsoftware

## Zielgruppe

Dieses Repo richtet sich an:

- den Architekten des Projekts
- zukünftige Mitwirkende
- spätere Nutzer, die das Add-in einsetzen oder erweitern möchten

## Fachliche Leitidee

Fusion 360 bleibt das CAD-System.

Die eigentliche Zuschnitt- und Produktionslogik bleibt bewusst außerhalb von Fusion und wird über CSV an externe Werkzeuge übergeben.

## Technische Leitplanken

- Windows als primäre Laufzeitumgebung
- Fusion 360 in der frei verfügbaren Version
- Python als derzeit bevorzugte Add-in-Technologie
- GitHub als zentrale Arbeits- und Dokumentationsbasis

## Inhaltliche Bausteine

- Physical Material für den Werkstoff
- Appearance für Kanten, Oberflächen und Fertigungszuordnung
- Attributes für Zusatzinformationen und Exportsteuerung

## Arbeitsregeln

- ein Issue pro Thema
- ein Thread pro Issue
- ein Pull Request pro Issue
- kein direkter Zugriff auf `main`
- Entscheidungen zuerst im Issue festhalten

## Verknüpfung zum Hauptprojekt

Dieses Repo liefert die Fusion-360-Seite zum Hauptprojekt `DIY Garage Cut`.
Änderungen hier sollten immer auf ein Ziel im Hauptprojekt oder auf eine klar abgegrenzte technische Aufgabe zurückführbar sein.

