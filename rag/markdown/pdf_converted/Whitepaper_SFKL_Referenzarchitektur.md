# Whitepaper_SFKL_Referenzarchitektur

## Seite 1

SmartFactory Referenzarchitektur
Standardisierte Vernetzung von IT und OT


Whitepaper SF 10/2025


# Whitepaper_SFKL_Referenzarchitektur

## Seite 2

Autoren
Simon Jungbluth, Benjamin Blumhofer, Carsten Harms, Pascal Rübel, Simon Bergweiler,
Prof. Dr. Martin Ruskowski

Impressum
Dieses Dokument ist unter dem Titel „SmartFactory Referenzarchitektur - Standardisierte Vernetzung von
IT und OT“ im Oktober 2025 von der Technologie-Initiative SmartFactory KL e. V. veröffentlicht und von
den hier aufgeführten Autoren verfasst worden. Es wird kostenlos verteilt und ist nicht zum Verkauf be-
stimmt.

Herausgeber
Technologie-Initiative SmartFactory KL e.V.
Trippstadter Straße 122
67663 Kaiserslautern

Stand: Oktober 2025


# Whitepaper_SFKL_Referenzarchitektur

## Seite 3

Vorwort
Seit zwei Jahrzehnten steht  die SmartFactoryKL für
Innovation, Zusammenarbeit und technologische
Weitsicht im Bereich der industriellen Produktion.
In dieser Zeit haben wir gemeinsam mit unseren
Partnern zukunftsweisende Konzepte entwickelt,
erprobt und in die Praxis überführt.
Im Folgenden präsentieren wir die SmartFactory Re-
ferenzarchitektur, welche Unternehmen einen kla-
ren Orientierungsrahmen bietet, um dem steigen-
den Markt- und Technologiedruck erfolgreich zu be-
gegnen. Sie unterstützt eine konsistente Datenstra-
tegie, ermöglicht die schrittweise Modernisierung
bestehender Produktionsumgebungen und sc hafft
durch Offenheit und Skalierbarkeit die Basis für die
Integration zukünftiger Schlüsseltechnologien.
Wir danken allen Mitwirkenden und freuen uns auf
die kommenden Jahre innovativer Zusammenar-
beit.















Inhalt

Einleitung und Motivation ................................. 1
Die Referenzarchitektur der SmartFactory ........ 2
OT-IT-Konvergenz für smarte Fabriken .......... 3
Mehr Wert schaffen durch kontextbezogene
Datenvernetzung .......................................... 4
Smarte Produktionssteuerung durch KI-
Agenten ........................................................ 5
Digital Twin-driven Manufacturing in fünf
Schritten ............................................................ 6
Anwendungsbeispiele ....................................... 6
Modularer Aufbau und Umsetzung der
Referenzarchitektur:
Produktionsinsel_PHUKET ............................ 7
Aktive Teilnahme im Manufacturing-X
Ökosystem .................................................... 9
Einheitliche, interoperable
Zugriffsmechanismen mit MCP in der
Produktion .................................................... 9
Verwaltungsschale als Enabler für
interoperables Wissensmanagement ......... 10
Shared Production ...................................... 10
Fazit ................................................................. 10
Literaturverzeichnis ......................................... 11


# Whitepaper_SFKL_Referenzarchitektur

## Seite 4

1

Einleitung und Motivation
Im Jahr 2022 hat die Task Force Manufacturing-X der
Plattform Industrie 4.0  [1] die Notwendigkeit „[…]
zur Entwicklung und Aufbau einer dezentral organi-
sierten Datenökonomie für die deutsche und euro-
päische Industrie […]“ [1] beschrieben. Treiber einer
solchen branchenübergreifenden industriepoliti-
schen Initiative sind unter anderem der wachsende
Wettbewerbsdruck auf die Industrie (z.B. durch Lie-
ferengpässe oder die Gefahr einer globalen Rezes-
sion) und zunehmende regulatorische  Anforderun-
gen (z.B. durch die europäische Kommission). Ziele
sind dabei die Erhöhung der Resilienz deutscher In-
dustrieunternehmen, um auf Störungen schnell re-
agieren und Wertschöpfungsnetzwerke neu organi-
sieren zu können, sowie der Erhalt und Ausbau der
Wettbewerbsstärke der deutschen Industrie auf
dem Weltmarkt. Damit das gelingt, braucht es eine
intelligente und vernetzte Industrie. In dieser müs-
sen Daten nahtlos integriert sein und die Unterneh-
men müssen bereit sein, sie sicher und vertrauens-
voll miteinander zu teilen. Dies erfordert die durch-
gängige Vernetzung der gesamten Wertschöpfungs-
kette aller Akteure. Mit Hinblick auf die von kleinen
und mittelständischen Unternehmen geprägte In-
dustrielandschaft in Deutschland entstehen neue
Herausforderungen:
• Unternehmen müssen sich in einem von mono-
polartigen Plattformbetreibern geprägten
Markt behaupten,
• die notwendige  digitale Transformation erfor-
dert tiefgreifende strukturelle Anpas sungen,
insbesondere durch die durchgängige Vernet-
zung und vertikale Integration von Daten von
der Fertigungsebene (Shopfloor) bis in die
Cloud,
• die auf dem Shopfloor vorherrschenden star-
ren, hardwaregebundenen Steuerungssysteme
müssen modernisiert und entkoppelt werden,
um die notwendige Flexibilität und Resilienz für
schnelle Reaktionen auf Marktveränderungen
zu schaffen,
• vor dem Hintergrund des demografischen Wan-
dels und des damit einhergehenden Fachkräfte-
mangels wird der strategische Umgang mit Wis-
sen und Daten immer wichtiger. Unternehmen
müssen ihr digitales Wissensfundament sichern
und ausbauen, um künftige Arbeitskräfte effek-
tiv einzuarbeiten und durch intelligente Sys-
teme bei komplexen Aufgaben zu unterstützen
[2].
Ausgehend von der Idee einer vernetzten Datenöko-
nomie wurde im Jahr 2024 die Initiative Manufac-
turing-X von der deutschen Regierung zur Verbesse-
rung der Wettbewerbsfähigkeit Deutschlands/Euro-
pas gestartet [3]. Dies erfordert eine gemeinsame
Grundlage für den Datenaustausch. Eine hersteller-
unabhängige, standardisierte und semantische
Struktur der Informationsmodelle für den Aus-
tausch maschinenlesbarer und interpretierbarer Da-
ten (1), eine standardisierte Kommunikation für au-
tomatisierte Verhandlungen und Datenaustausch
(2), sowie eine föderierte und sichere Dateninfra-
struktur in Übereinstimmung mit den europäischen
Gesetzen (3) sind nun notwendig [4]. Die Vernet-
zung und Digitalisierung ist dabei ein entscheiden-
der Treiber, um neue Wertschöpfungspotentiale zu
erschließen. Hierzu müssen Assets, in unserem Kon-
text materielle oder immaterielle Gegenstände von
Wert für die Produktion [5], herstellunabhängig und
interoperabel beschrieben werden, um eine über-
greifende Kommunikation der OT und IT zu ermögli-
chen [6]. Dies wird realisiert, indem alle industriel-
len Assets und Dienste standardisierte Datenmo-
delle und Schnittstellen besitzen.  Die Integration
von Hard - und Softwarekomponenten kann durch
die standardisierte Selbstbeschreibung nahtlos er-
folgen, was sowohl die realen als auch die virtuellen
Strukturen resilienter gestaltet.
Fundament vernetzter Wertschöp-
fungssysteme
Zur Realisierung einer durchgängigen Vernetzung
existieren unterschiedliche Interoperabilitätslösun-
gen [7], welche in verschiedenen Lebenszykluspha-
sen verwendet werden können. Das Referenzarchi-
tekturmodell Industrie 4.0 (RAMI 4.0)  [8] definiert
einen strukturierten Rahmen zur systematischen
Einordnung technischer, organisatorischer und se-
mantischer Standards im Kontext von Industrie 4.0.
Zur Integration der Shopfloor Ebene kommen fol-
gende drei Standards [9] zur Anwendung:


# Whitepaper_SFKL_Referenzarchitektur

## Seite 5

2

• AutomationML – für die Asset-Entwicklung so-
wie die Planung des produktiven Einsatzes,
• OPC UA – für den produktiven Einsatz sowie die
Wartung des Assets,
• Verwaltungsschale (VWS) – für die Kommunika-
tion der vernetzen Welt, zuzüglich aller Inhalte
(wie Typenschild, Stückliste, CO2-Fußabdruck
(PCF), etc.), die dem hergestellten Produkt zu-
geordnet werden können.
Ein weiterer Baustein in der  Schaffung vernetzter
Systeme ist der souveräne Datenaustausch. Dazu
bietet Gaia-X [10] einen Satz an international gelten-
den Regeln, Standards und Governance-Strukturen.
Dabei spielen technische Konzepte und Protokolle
der International Data Spaces Association (IDSA)
[11], [12] eine zentrale Rolle, insbesondere für den
vertrauenswürdigen Datenaustausch, die Durchset-
zung von Daten-Nutzungsrichtlinien sowie den Auf-
bau interoperabler und föderierter Datenräume.
Erste Ausprägungen für domänenspezifische Daten-
räume sind beispielsweise Catena-X [13] für die Au-
tomobilbranche oder smartMA-X [4] für den Ferti-
gungsbereich. In diesem Zuge entwickelte Catena-X
den sog. Eclipse Dataspace Connector [14], welcher
sich auf die Spezifikationen von Gaia -X stützt und
das Datenraumprotokoll der IDSA implementiert. Im
Folgenden wird der Begriff Konnektor verwendet,
um die Anbindung an einen Datenraum zu beschrei-
ben. Eine stark vereinfachte Darstellung eines Da-
tenraums kann Abbildung 1 entnommen werden.
In digitalen Datenräumen arbeiten verschiedene
Unternehmen und Organisationen zusammen, oft
ohne sich persönlich zu kennen. Damit diese
Kollaboration sicher und effizient funktioniert,
braucht es ein technisches Vertrauensmodell. Die-
ses basiert auf dem sogenannten Issuer–Holder–Ve-
rifier-Prinzip [15]. Alle Beteiligten verfügen über
eine eigene dezentrale Identität (DID), die eine si-
chere und eindeutige Identifikation ermöglicht. Auf
dieser Grundlage kann jede Partei (Verifier) selbst
entscheiden, welchen Herausgebern (Issuern ) von
digitalen Nachweisen sie vertraut und welche Infor-
mationen sie von den Inhabern (Holdern) akzep-
tiert.
Nach der Definition grundlegender Konzepte für
vertrauenswürdigen Datenaustausch rückt nun die
konkrete Umsetzung in den Fokus: Mit der Smart-
Factory Referenzarchitektur liegt ein anwendungs-
nahes Architekturmodell vor, das die strukturelle
und funktionale Vernetzung von OT - und IT-Syste-
men in der Fabrik ermöglicht. Sie schafft damit die
technische Grundlage für Interoperabilität, Modula-
rität und sicheren Datenaustausch in  digitalisierten
Produktionsumgebungen.
Die Referenzarchitektur der Smart-
Factory
Mit der folgenden Referenzarchitektur der Smart-
Factory wird eine Grundlage für die nahtlose In-
tegration von IT - und OT-Systemen geschaffen und
eine durchgängige Datenvernetzung vom Shopfloor
bis in die vernetzte Welt ermöglicht. Die Architektur
soll dabei zeigen, wie Komponenten intelligent ge-
kapselt und verknüpft werden können. Hierdurch
sollen neue Geschäftsmodelle entstehen, Innovatio-
nen beschleunigt , Inbetriebnahmezeiten verkürzt ,
die Variantenvielfalt erhöht und die Flexibilisierung
von Anlagen erhöht werden. Wichtig dabei ist, be-
stehende Investments zu schützen und existierende
Applikationen zu integrieren. Abbildung 2 repräsen-
tiert die Bausteine der Referenzarchitektur. Die Re-
ferenzarchitektur gliedert sich in ein klar strukturier-
tes dreischichtiges Modell, dass die einzelnen funk-
tionalen Ebenen einer Fabrik vom physischen
Shopfloor bis zur übergeordneten IT -Infrastruktur
systematisch abbildet. Diese strukturierte Gliede-
rung hat zum Ziel , eine Zuordnung von Funktionen,
Schnittstellen und Verantwortlichkeiten abzubilden,
die sowohl die vertikale Integration als auch die Abbildung 1: Komponenten des Datenraums


# Whitepaper_SFKL_Referenzarchitektur

## Seite 6

3

horizontale Skalierbarkeit industrieller Systeme un-
terstützt:
OT-Ebene: Diese unterste Schicht umfasst Feldge-
räte, Sensorik und Aktorik, die direkt mit der physi-
schen Produktionsumgebung interagieren. Sie bil-
det die Grundlage für die Datenerfassung und Pro-
zessausführung.
IT/OT-Kopplungsebene: Als vermittelnde Schicht in-
tegriert diese Ebene Edge-Komponenten und Steue-
rungen. Sie ermöglicht die sichere und performante
Kommunikation zwischen operativen Systemen und
IT-Diensten und bildet die Schnittstelle für Datenag-
gregation, Vorverarbeitung und Steuerung.
IT-Ebene: Die oberste Schicht kapselt alle überge-
ordneten Applikationen, von klassischen ERP - und
MES-Systemen bis hin zu agentenbasierten Diens-
ten und KI-gestützten Analysemodulen. Sie stellt die
zentrale Instanz für Planung, Optimierung und da-
tengetriebene Entscheidungsfindung dar.
OT-IT-Konvergenz für smarte Fabriken
Betrachtet man die Feldbusebene, zeigt sich, dass
sich im Laufe der Zeit zahlreiche unterschiedliche
Abbildung 2: Referenzarchitektur der SmartFactoryKL


# Whitepaper_SFKL_Referenzarchitektur

## Seite 7

4

Bussysteme und Protokolle entwickelt haben. Dies
ist vor allem darauf zurückzuführen, dass verschie-
dene Hersteller spezifische Anforderungen einzel-
ner Branchen durch eigene, teils proprietäre Lösun-
gen abgedeckt haben.  Die klassischen Bussysteme
werden in der Architektur durch Speicherprogram-
mierbare Steuerungen (SPS) und die zugehörigen
Aktoren und Sensoren umgesetzt.  Dies erschwert
die Integration neuer Geräte in einer existierenden
Produktion. Die neue Generation an Feldgeräten
(smarte Sensor en und smarte  Aktoren) beschreibt
Geräte, welche eigenständig funktionieren und das
direkte Auslesen von Informationen oder Ansteuern
von Aktoren über definierte Schnittstellen des Edge
Layers unterstützen. Beispiele sind RFID -Sensoren,
welche direkt eine Weboberfläche zum Auslesen
der Tags bereitstellt oder ein Roboter, welcher vor-
definierte Jobs ausführen kann. In der Referenzar-
chitektur findet die Integration dieser smarten Ge-
räte nicht mehr in einer klassischen SPS statt, son-
dern auf Edge-Geräten. Diese müssen dabei sowohl
den Anforderungen an Echtzeit als auch hohen Si-
cherheitsstandards genügen. 1 Zur Integration ste-
hen sog. Interface Applikatione n bereit, welche die
Daten aus den einzelnen Schnittstellen auf einen di-
gitalen OT-Datenbus ablegen. An dieser Stelle endet
die klassische Automatisierung, da die Daten aus
der Feldebene nun unabhängig von herkömmlichen
Steuerungssystemen verarbeitet und in frei wählba-
ren Programmiersprachen weiterverwendet wer-
den können.
Hier greifen eine smarte Maschinensteuerung
(Smart Machine Logic Controller) und gekapselte
Automatisierungsfunktionen – sogenannte Skills –
ineinander. Skills stellen die ausführbare Implemen-
tierung einer gekapselten Automatisierungsfunk-
tion dar und erlauben dabei die flexible Inbetrieb-
nahme und Rekonfiguration von Produktionssyste-
men [16].  Anstelle einer gerätezentrierten Sicht-
weise erfolgt die Betrachtung von Feldgeräten und
Maschinen zunehmend funktionsorientiert.   Die
smarte Maschinensteuerung verpackt dabei die
proprietären Schnittstellen der SPSen, smarten Sen-
soren und smarten Aktoren in modulare Skills. Er-
gänzend besteht die Möglichkeit , auf bestehende

1 Beispiele für diese Automatisierungslösungen sind die ctrlX Au-
tomation (Bosch Rexroth) oder die  Industrial Edge (Siemens)
Skills smarter Maschinen zuzugreifen und diese wie-
derzuverwenden. Auf Basis der verfügbaren Skills
leitet die smarte Maschinensteuerung komplexe,
höherwertige Funktionen ab.  Zum einen sind diese
höherwertigen Funktionen sehr flexibel, zum ande-
ren können sie problemlos angepasst werden, ohne
dass der eingebettete Steuerungscode modifiziert
werden muss.   Außerdem kann die zugrunde lie-
gende Hardware ausgetauscht werden, ohne dass
Änderungen an den Skills erforderlich sind.
Die smarte Maschinenschnittstelle (Smart Machine
Interface) verarbeitet und wandelt die operativen
Daten des OT -Datenbusses in ein standardisiertes
Format um und fungiert als zentraler Zugriffspunkt
auf das Netzwerk der Maschine.  Hierzu empfehlen
wir OPC UA for Machinery [17], [18]. So lässt sich der
interoperable Maschinenzustand erfassen, die Pro-
zessüberwachung realisieren  und die semantische
Dateninterpretation ermöglichen . Dabei können
durch sog. Bausteine  die Skills der Komponenten
verfügbar gemacht werden [19]. Die standardisierte
Maschinenschnittstelle erlaubt die Nutzung und
Wiederverwendung einheitlicher Maschinenbe-
dienoberflächen und Auswertetools. Dadurch müs-
sen zum einen keine individuellen Lösungen für die
Maschinensteuerung (z. B. WinCC) mehr entwickelt
werden. Zum anderen erleichtert die standardi-
sierte Bedienoberfläche die Handhabung neuer Ma-
schinen, da Bediener sich schneller mit den Funkti-
onen vertraut machen können. Dies führt zu ver-
kürzten Einarbeitungszeiten, reduziert Fehlerquel-
len und steigert insgesamt die Effizienz im Produkti-
onsprozess.
Mehr Wert schaffen durch kontextbezogene
Datenvernetzung
Verlässt man die IT/OT-Ebene, reicht es nicht mehr
aus, sich nur auf operative Daten zu fokussieren,
vielmehr muss der gesamte Lebenszyklus der Assets
berücksichtigt werden. Die Verwaltungsschale fun-
giert als zentraler Zugangspunkt für sämtliche Da-
tenpunkte eines Assets und ermöglicht die Verknüp-
fung dezentraler Datenquellen über standardisierte
Schnittstellenbeschreibungen [20]. Dadurch wird
eine einheitliche Sicht auf heterogene


# Whitepaper_SFKL_Referenzarchitektur

## Seite 8

5

Datenbestände geschaffen, die statische Informati-
onen wie Stammdaten, technische Spezifikationen
oder Betriebsparameter und auch dynamische Ma-
schinendaten umfassen. Bestehende und individu-
elle Anwendungen 2 können durch die Konvertie-
rung herstellerspezifischer Daten in VWS -konforme
Formate nahtlos in die Referenzarchitektur inte-
griert werden , wodurch ein durchgängiger Daten-
austausch zwischen Anwendungen geschaffen wer-
den kann . Unterschiedliche Datenquellen , wie die
smarte Maschinenschnittstelle und existierende
Komponenten können genutzt werden, um Daten
standardisiert und automatisiert zu aggregieren .
Diese aggregierten Daten ermöglichen es, Berichte
zu erstellen, die den Anforderungen an Transparenz
und Nachvollziehbarkeit im gesamten Asset-Lebens-
zyklus gerecht werden.
Die standardisierten Strukturen des digitalen IT-Da-
tenbusses ermöglichen es , Daten über einen
Konnektor direkt an bestehende Datenräume anzu-
binden. Der Konnektor gliedert sich dabei in das
existierende Zugriffsrechtemanagement des Unter-
nehmens ein und gibt die Zugriffe entsprechend
über vereinbarte Richtlinien an berechtige Akteure
frei. Somit wird  Vertrauen, Datensouveränität und
Sicherheit innerhalb des Ökosystems gewährleistet.
Dank der semantischen Beschreibung der Daten ist
es möglich, sowohl interne als auch externe Daten-
quellen nahtlos in den unternehmensinternen Da-
tenbus zu integrieren. Dies schafft die Grundlage für
eine datenzentrierte Unternehmenssteuerung, bei
der die Herkunft der Daten unerheblich ist ; ent-
scheidend ist der geschaffene Mehrwert durch eine
konsistente und skalierbare Nutzung über System -
und Unternehmensgrenzen hinweg. Gerade für An-
wendungen mit Künstlicher Intelligenz (KI)  bietet
dies große Vorteile . Der Zugriff auf kontextuell be-
schriebene Daten ermöglicht es , KI-Informationen
effizient zu analysieren, Muster schneller zu erken-
nen und fundierte Vorhersagen zu treffen. Gleichzei-
tig reduziert die einheitliche Struktur den Aufwand
für Vorverarbeitung und schafft eine verlässliche
Grundlage, wodurch KI schneller einsetzbar sowie

2 Unter Legacy- und individuellen Anwendungen sind alle beste-
henden Anwendungen einer Organisation zu verstehen. Dazu
präziser, transparenter und unternehmensweit ska-
lierbar wird.
Smarte Produktionssteuerung durch KI-Agen-
ten
Über den IT -Datenbus als zentralen Einstiegspunkt
können dezentrale, autonome Entitäten in die Steu-
erung moderner Fabriken integriert werden. Dabei
müssen die Zusammenhänge zwischen Datenpunk-
ten erkannt, Entscheidungen abgeleitet und die Pro-
duktionsziele im Einklang mit der übergeordneten
Unternehmensstrategie verfolgt werden. Um diese
Anforderungen zu erfüllen, setzen wir auf auto-
nome intelligente Einheiten, sogenannte Agenten
[21]. Agenten agieren eigenständig und verfolgen
ein Ziel, sind aber in der Lage, mit anderen Einheiten
zu kooperieren. Dieses Prinzip bildet die Grundlage
eines Produktionskonzepts, das speziell darauf aus-
gelegt ist, die Flexibilität, Skalierbarkeit und Anpas-
sungsfähigkeit von Fertigungssystemen zu erhöhen,
etwa zur Unterstützung der Produktindividualisie-
rung oder im Umgang mit unvorhersehbaren Be-
triebsbedingungen [22]. Diese Agenten verwalten
einzelne Assets (insbesondere Produkte und Res-
sourcen wie Fertigungsinseln, Module, Handarbeits-
plätze oder Transporteinheiten) und repräsentieren
den proaktiven Teil eines Assets. Wir verwenden
eine Untergliederung in Service Agent en, Produ kt
Agenten und Ressourcen Agenten. Service Agenten
übernehmen die Koordination des unternehmens-
übergreifenden Datenaustauschs sowie die Aus-
handlung und Bereitstellung von Services innerhalb
eines Datenraums  durch Verwendung von
Konnektoren. Sie verhandeln den Zugriff auf Daten-
ressourcen auf Basis definierter Richtlinien. Der Pro-
dukt Agent ist für die Produktionsplanung und
-terminierung verantwortlich und leitet in Koopera-
tion mit dem Ressourcen Agenten konkrete Produk-
tionsaufträge ab. Der Ressourcen Agent ist für die
Ausführung von Produktionsaufträgen verantwort-
lich und optimiert dabei die Zeitplanung und Auslas-
tung der jeweiligen Maschine [23], [24].
zählen unter anderem ERP-, CAD- und CAM-Systeme sowie spe-
ziell für die Organisation entwickelte Lösungen.


# Whitepaper_SFKL_Referenzarchitektur

## Seite 9

6

Digital Twin-driven Manufacturing in
fünf Schritten
Die vorgestellte Referenzarchitektur skizziert die di-
gitale Struktur einer selbstorganisierenden  Fabrik,
welche durch digitale Zwillinge gesteuert wird. Die
Vision der selbstorganisierten Fabrik lässt sich nicht
mit einem einzigen Technologiesprung realisieren,
sie ist das Ergebnis eines schrittweisen, systematisch
aufgebauten Transformationsprozesses. Abbildung
3 zeigt dabei, wie Unternehmen in fünf klar definier-
ten Etappen von manuellen Abläufen hin zu auto-
nom gesteuerten Produktionsprozessen gelangen
können.
Der erste Schritt bildet die Basis für alle weiteren
Entwicklungen. Investitionen in digitale Standards
und Schnittstellen legen das Fundament für die
langfristige Flexibilität und Skalierbarkeit der Fabrik.
Maschinen, Anlagen und IT-Systeme müssen über
einheitliche Datenmodelle und standardisierte
Schnittstellen miteinander kommunizieren können.
Der Einsatz der Verwaltungsschale und OPC UA legt
das notwendige Fundament für eine durchgängige
Datenverfügbarkeit, sowohl vertikal ü ber System-
grenzen hinweg als auch horizontal über den
Shopfloor verteilt. Sind die grundlegende n Daten-
flüsse etabliert, gilt es, die Qualität der Daten syste-
matisch zu verbessern.
Im zweiten Schritt dienen zuverlässige Daten als
Grundlage, um fundierte Entscheidungen zu treffen.
Durch erste Analysefunktionen entsteht ein klarer,
datenbasierter Blick auf Prozesse, Engpässe und
Potenziale. Relevante Informationen werden auto-
matisch bereitgestellt, sodass Abweichungen früh-
zeitig erkannt und Nachsteuerungen zeitnah einge-
leitet werden können. Analysierte Daten können für
ein automatisiertes Reporting genutzt werden.
Im dritten Schritt werden die Erkenntnisse aus den
vorangegangenen Analysen genutzt, um konkrete
Optimierungsmaßnahmen abzuleiten. Durch daten-
basierte Prozessverbesserungen lassen sich die Effi-
zienz steigern, Kosten senken und die Wettbewerbs-
fähigkeit stärken.
In Schritt vier entsteht durch die Einführung digitaler
Agenten für Produkte und Ressourcen ein Netzwerk
autonom interagierender Einheiten.  Diese Agenten
ermöglichen eine dezentrale Steuerung. Produkte
können Anforderungen kommunizieren, Ressourcen
ihren aktuellen Status und ihre Verfügbarkeit mel-
den: das bildet die Grundlage für eine dynamische
Entscheidungsfindung.
Im fünften Schritt kooperieren Produkte und Res-
sourcenagenten eigenständig, um Produktionsauf-
träge effizient und flexibel umzusetzen.  Die Fabrik
reagiert in Echtzeit auf Veränderungen, organisiert
Abläufe selbstständig und passt sich dynamisch an
neue Anforderungen an.
Anwendungsbeispiele
Die nachfolgenden Abschnitte zeigen anhand ausge-
wählter Anwendungsbeispiele, wie die Referenzar-
chitektur Mehrwert e liefert. Effiziente Steuerungs-
lösungen, dynamische Auftragsabwicklung und die
Abbildung 3: Digital Twin-driven Manufacturing in fünf Schritten


# Whitepaper_SFKL_Referenzarchitektur

## Seite 10

7

nahtlose Integration moderner KI -Anwendungen
zeigen, wie Prozesse nachhaltig optimiert werden.
Modularer Aufbau und Umsetzung der Refe-
renzarchitektur: Produktionsinsel_PHUKET
Die Produktionsinsel_PHUKET ist ein erstes Beispiel
für die Implementierung der oben beschriebenen
Referenzarchitektur (siehe Abbildung 4). _PHUKET
besteht aus  insgesamt fünf  modular gekapselten
Produktionseinheiten, welche über standardisierte
Hardware- und Softwareschnittstellen frei konfigu-
rierbar sind. Die fünf Produktionsmodule untertei-
len sich in ein Lagermodul , zwei Montagemodule ,
ein Lasermodul und ein zentrales Handhabungsmo-
dul in der Mitte, welches Produkte zu den einzelnen
Zellen transportiert. Die nachfolgende Erläuterung
der Referenzarchitektur wird in zwei Abschnitte un-
terteilt. Zunächst wird an dem Beispiel einer Pro-
duktionseinheit erläutert, wie über die Edge-Geräte
eine smarte Maschinenschnittstelle geschaffen wer-
den kann. Im Anschluss wird anhand eines Produk-
tionsbeispiels gezeigt, wie das Produkt die Fertigung
selbstständig steuert.
Realisierung einer smarten Maschine
Auf _PHUKET wird eine Produktionseinheit zu einer
smarten Maschine, indem die Logik der Steuerung
in ein Edge Gerät ausgelagert wird. Nachfolgend
stellt Abbildung 5 die Bausteine eines Montagemo-
duls dar, welches in Kombination mit dem We rker
Produkte zusammenbaut . Dieses Montagemodul
besitzt einen Roboter inklusive Greifer zur Anliefe-
rung von Produkten, RFID-Ausleseeinheiten zur
Identifikation der Produkte im Lager und einer klas-
sischen Speicherprogrammierbaren Steuerung zur
Realisierung sicherheitskritischer Aspekte . Der Ro-
boter ist dabei mit einer eigenen app-basierten Kon-
trolleinheit ausgestattet, wodurch der Roboter ge-
mäß der Architektur als smarte Maschine agiert.
Als Edge Lösung wurde auf die  Siemens Industrial
Edge1 zurückgegriffen. Hier bei können sowohl di-
rekt Apps aus dem Siemens-internen Appstore (z.B.:
S7 Interface App zur Integration der SPS), als auch
eigene Applikationen (z.B.: AutoID OPC UA Interface
App für den Datenzugriff auf smarte RFID-Sensoren
[25], HTTP REST Interface App zur Ansteuerung des
Greifers und gRPC Interface App zur Kontrolle des
Roboters) verwendet werden , um die Daten aus
dem Feld in der Edge zu integrieren. Die Maschinen-
steuerung (Smart Machine Logic Controller) wurde
in Python umgesetzt und dient zur Orchestration an-
derer Skills.
Hierzu werden proprietäre Ansteuerungsmöglich-
keiten in atomare Skills gekapselt und zusammenge-
setzte Skills abgeleitet. Diese stehen nun zur Verfü-
gung, um mit Hilfe von Fähigkeiten flexibel auf Pro-
duktionsanfragen reagieren zu können. Die smarte
Maschinenschnittstelle wird durch ein OPC UA Infor-
mationsmodell realisiert, welche die OPC UA Machi-
nery [18] mit dem Skill-basierten Ansatz kombiniert.
Um auf diese Skills  zugreifen zu können, wird über
die Asset Interface Description [20] der VWS auf die-
sen referenziert. Somit wird die OPC UA Schnittstelle
mit dem IT -basierten Datenbus integriert referen-
ziert.

Abbildung 4: Darstellung der
Produktionsinsel_PHUKET


# Whitepaper_SFKL_Referenzarchitektur

## Seite 11

8

Das Produkt steuert sich selbst durch die Produk-
tion
Zur Arbeitsplanung werden die angebotenen Fähig-
keiten (Capabilities3) von Maschinen und die benö-
tigten Fähigkeiten in Form von Fertigungsfeatures in
der VWS abgebildet. Die VWS stellt an dieser Stelle
das Informationsmodell und den Datenzugriff be-
reit, ist aber rein reaktiv. Agenten für Ressourcen
und Produkte dienen dazu, dem Produktionssystem
eine aktive Komponente hinzuzufügen . P rodukta-
genten begleiten das Produkt durch den gesamten
Produktionsprozess und arbeiten gleichberechtigt
mit den Ressourcenagenten zusammen, um eine
flexible und reaktionsfähige Fertigung zu ermögli-
chen. Dies funktioniert so:  Features des Produkts
enthalten eine Beschreibung der individuellen  Ei-
genschaften. Anhand dieser Features können mit-
hilfe von Domänenwissen die erforderlichen Fähig-
keiten abgeleitet werden, die zur Fertigung der Fea-
tures notwendig sind. Durch einen Abgleich, das so-
genannte „Matchmaking“, zwischen den benötigten
Fähigkeiten und den Fähigkeiten der Produktions-
ressourcen lassen sich potenzielle Kandidaten für
die jeweiligen Fertigungsschritte identifizieren . Aus

3 Das Submodell CapabilityDescription wird von der IDTA stan-
dardisiert (Stand 10.10.2025)
den ermittelten Kandidatengruppen entstehen
mehrere Arbeitspläne, die unterschiedliche Ausfüh-
rungsmöglichkeiten abbilden. Soll ein Produkt konk-
ret gefertigt we rden, findet eine Ausschreibung
statt. Ressourcenagenten bewerben sich entspre-
chend der Verfügbarkeiten. Dabei werden  sowohl
globale Zielkriterien der Ausschreibung (globale Op-
timierung) als auch  lokale Aspekte ( Zustände und
hinterlegte Maschinenaufträge  - lokale Optimie-
rung) berücksichtigt. Die Ressourcenagenten leiten
aus den abstrakten Fähigkeitsbeschreibungen kon-
krete Skillsequenzen ab , steuern und überwachen
die jeweiligen Maschinen über die smarte Maschi-
nenschnittstelle und übermitteln die Ausführung s-
daten an den Produkt Agenten. Die Produkt Agenten
nutzen diese Daten, um produktindividuelle  Doku-
mentationen, wie beispielsweise einen PCF, voll-
ständig zu automatisieren.
Abbildung 5: Darstellung der Steuerungsarchitektur einer smarten Maschine


# Whitepaper_SFKL_Referenzarchitektur

## Seite 12

9

Aktive Teilnahme im Manufacturing-X Ökosys-
tem
Zur Umsetzung der Vorhaben in der Initiative Manu-
facturing-X [3] ist eine projektübergreifende Zusam-
menarbeit domänenspezifischer Projekte notwen-
dig.  Das Projekt Factory -X [26] definiert mit dem
sog. MX-Port [27] ein konfigurierbares und offenes
Konzept für einen dezentralisierten, vertrauenswür-
digen und sicheren Datenaustausch . Daten können
standardisiert und kontrolliert über Unternehmens-
grenzen hinweg ausgetauscht werden.  Das MX-Port
Konzept gliedert den Datenaustauch in fünf klar de-
finierte Ebenen (siehe Tabelle 1). Dabei werden un-
terschiedliche Konfigurationen durch die Zuordnung
von ausgewählten Komponenten für die einzelnen
Schichten definiert. Potenzielle Kandidaten sind da-
bei beispielsweise die Verwaltungsschalen -Submo-
delle  [28], OPC UA Companion Spezifikationen [29]
oder das Dataspace Protokoll  [12]. Die dargestellte
Referenzarchitektur zeigt dabei, wie d ie einzelnen
Schichten des MX-Ports in einem Unternehmen um-
gesetzt werden können (siehe Abbildung 6).
Einheitliche, interoperable Zugriffsmechanis-
men mit MCP in der Produktion
Das Model Context Protocol (MCP) [30] ist ein Open-
Source-Framework und -Standard, der es Systemen
mit künstlicher Intelligenz, insbesondere großen
Sprachmodellen (LLMs), ermöglicht, sich nahtlos
mit externen Tools, Datenquellen und Systemen zu
verbinden. Durch standardisierte und semantische
Informationsmodelle können LLMs dabei den Ko n-
text interpretieren und entfalten ihre volle Wirk-
samkeit. Durch die Nutzung einer standardisierten
Maschinenschnittstelle mit Hilfe von OPC UA und
den Einsatz der Verwaltungsschale liegen die Daten
innerhalb der Referenzarchitektur semantisch be-
schrieben vor. Durch MCP können LLMs direkt mit
diesen Schnittstellen interagieren. So können Daten
mit natürlicher Sprache abgefragt werden. Interakti-
onen wie „ wie viele  Teile wurden in der letzten
Stunde produziert?“ oder „ verfahre die Achse !“
werden dadurch automatisiert und ohne Mehrauf-
wand realisiert.



Edge Devices
Smart Machine Logic
Controller App
• Atomic Skills
• Composite Skills
OT Data Layer
Smart Machine
Interface App
Interface App
Programmable
Logic
Controller
Sensor
 Actuator
Field Devices
e.g.,
Profinet
Connector
IT Data Layer
AAS
External Data
L1
L2
L3
L4
L5
Schicht
(L1-5) Funktion
Discovery
L5
… wird verwendet, um Geschäftspartner,
Datenbestände (z. B. Geräte) oder Ge-
schäftsanwendungen zu finden.
Access &
Usage
Control
L4
… wird verwendet, um sicherzustellen,
dass Datenanbieter den Datenzugriff und
die Datennutzung definieren sowie den
Zugriff und die Nutzung der bereitgestell-
ten Daten einschränken können.
Gate
L3
… wird verwendet, um Daten auf einheitli-
che Weise auszutauschen.
Converter
L2
… stellt das semantische Modell für die
auszutauschenden Daten bereit.
Adapter
L1
… ermöglicht den Datenzugriff durch eine
applikationsspezifische Datenanbindung.

Tabelle 1: Darstellung der Schichten bzw. Layer (L) des
MX-Ports [27]
Abbildung 6: Integration des MX-Ports in die
SmartFactory Architektur


# Whitepaper_SFKL_Referenzarchitektur

## Seite 13

10

Verwaltungsschale als Enabler für interoperab-
les Wissensmanagement
An der Herstellung von Produkten sind viele ver-
schiedene Entitäten in der Fertigung beteiligt, die
viele Daten erzeugen. Gleichzeitig existieren große
Mengen an Wissen und Informationen über die En-
titäten und ihre Beziehungen zueinander. Dies kann
in den digitalen Zwillingen der Entitäten durch den
Einsatz von Verwaltungsschalen interoperabel abge-
bildet werden. Auch die Beziehungen zwischen den
beteiligten Elementen können in Verwaltungsscha-
len dargestellt werden.
Um komplexe Zusammenhänge abbilden zu können,
eignen sich Wissensgraphen , die grundlegend ein
Netzwerk aus Entitäten, Properties und deren Bezie-
hungen darstellen. Damit die große Informations -
und Datenmenge, die in den Verwaltungsschalen
abgelegt und referenziert ist, effizient nutzbar ge-
macht werden kann, werden Verwaltungsschalen in
Form von Wissensgraphen dargestellt. Die beiden
Repräsentationen existieren dabei nebeneinander
und synchronisieren sich gegenseitig. Das Me tamo-
dell der Verwaltungsschale und  deren Infrastruktur
bildet dafür die strukturelle Grundlage.
Durch die dezentrale Vernetzung der Verwaltungs-
schalen und die mächtigen Abfragemöglichkeiten
von Graphdatenbanken k ann das abgebildete Wis-
sen für verschiedene Anwendungen genutzt wer-
den. Zunächst wird es möglich, Abfragen an das ver-
teilte System zu stellen, wie bspw. „Ist ein AGV ver-
fügbar, welches ein Produkt mit einem Gewicht von
5 kg transportieren kann?”. Der Wissensgraph kann
entweder direkt abgefragt werden oder in Kombina-
tion mit MCP als Eingangsquelle zur Interaktion mit
dem Nutzer in natürlicher Sprache.
Des Weiteren sind komplexere Analysen möglich ,
bei denen Ähnlichkeitsalgorithmen eingesetzt wer-
den. Hier können z.B. aufgetretene Fehlerfälle mit
Fehlern von anderen Maschinen verglichen werden.
Handlungsempfehlungen, die an anderer Stelle be-
reits etabliert sind, können dadurch auch hier einge-
setzt werden.
Shared Production
Eine digitale Plattform oder ein dezentrales Produk-
tionsnetzwerk, das automatisiert Auftraggeber mit
Auftragsfertigern verbindet und gleichzeitig resili-
ente Lieferketten fördert, bietet das Potenzial, die
Beschaffungskosten von Unternehmen zu reduzie-
ren und die Auftragsvergabe bis hin zur Maschinen-
ebene effizient zu steuern. Damit Shared Production
funktioniert, müssen Unternehmen miteinander
vernetzt sein, ihre Dienstleistungen anbieten sowie
effektiv kommunizieren können, um eine gemein-
same Lieferkette zu bilden. Darüber hinaus müssen
sie in der Lage sein, Produktionsanfrage n intern zu
bearbeiten und umzusetzen. Im Projekt smartMA-X
[4] konnte gezeigt werden, wie eine solche Produk-
tion umgesetzt werden kann.
Mit der Referenzarchitektur der SmartFactory wird
nun gezeigt, wie sich Unternehmen durch den Ein-
satz der Verwaltungsschale und Konnektoren in ein
solches Datenökosystem eingliedern k önnen.
Dienstleistungen können über die VWS interopera-
bel angeboten oder aufgerufen werden und direkt
in die unternehmensinterne Datenstruktur eing e-
gliedert werden. Als Beispiel dient hier _PHUKET als
Teil der Shared Production Kaiserslautern (siehe Ab-
bildung 7) und Bereitsteller von  Dienstleistungen
wie beispielsweise der Montage.

Fazit
Die vorgestellte Referenzarchitektur bietet produ-
zierenden Unternehmen einen klaren Orientie-
rungsrahmen, um den steigenden Markt- und Tech-
nologiedruck souverän zu  bewältigen. Sie unter-
stützt eine konsistente Datenstrategie, ermöglicht
eine schrittweise Modernisierung bestehender
Abbildung 7: Shared Production Kaiserslautern


# Whitepaper_SFKL_Referenzarchitektur

## Seite 14

11

Produktionsumgebungen und schafft durch Offen-
heit und Skalierbarkeit die Voraussetzungen für die
Integration zukünftiger Schlüsseltechnologien.
Zusammengefasst bedeutet dies:
• Wettbewerbsfähigkeit durch Interoperabilität
in einem plattformdominierten Markt,
• Effizienzsteigerung durch durchgängige Daten-
verfügbarkeit und intelligente Systeme,
• Wissenssicherung und -weitergabe trotz Fach-
kräftemangel,
• und Innovationspotenziale durch KI, datenba-
sierte Services und flexible Produktionsketten.
Die Anwendungsbeispiele zeigen eindrücklich: Die
SmartFactory Referenzarchitektur bildet eine belast-
bare Grundlage für nachhaltigen Erfolg in einer ver-
netzten, datengetriebenen und kollaborativen In-
dustrie. Damit bietet sie heute einen Referenzrah-
men und unterstützt morgen die nachhaltige Trans-
formation industrieller Prozesse.

Literaturverzeichnis
[1] Bundesministerium für Wirtschaft und Klimaschutz
(BMWK), Hrsg., „Whitepaper ‚Manufacturing -X‘: Eckpunkte für
die Umsetzung von ‚Manufacturing -X‘ im produzierenden Ge-
werbe zur Sicherung des Wettbewerbsstandortes Deutschland“.
2022. Zugegriffen: 14. Oktober 2025. [Online]. Verfügbar unter:
https://www.plattform-i40.de/IP/Redaktion/DE/Down-
loads/Publikation/Manufacturing-X_lang.pdf?__blob=publica-
tionFile&v=2
[2] Deutsche Industrie - und Handelskammer (DIHK),
Hrsg., „Fachkräftemangel trifft auf Strukturprobleme Neuer
DIHK-Report mit konkreten Vorschlägen zur Mobilisierung von
Personal“. 2024. Zugegriffen: 14. Oktober 2025. [Online]. Verfüg-
bar unter: https://www.dih k.de/re-
source/blob/127242/6ffb666cfa53e926e07b3cf91d5d021f/fach
kraefte-dihk-report-fachkraeftesicherung-2024-2025-data.pdf
[3] Bundesministerium für Wirtschaft und Energie, „För-
derprogramm ‚Manufacturing-X‘ Die Unterstützung des Daten-
ökosystems für eine intelligent vernetzte Industrie Einleitung“.
Zugegriffen: 14. Oktober 2025. [Online]. Verfügbar unter:
https://www.bundeswirtschaftsministerium.de/Redak-
tion/DE/Dossier/manufacturing-x.html
[4] S. Jungbluth u. a., „smartMA-X: Mit Datenräumen in
die Produktion der Zukunft“. SmartFactory-KL, 2024.
[5] Industrial Digital Twin Association, Specification of the
Asset Administration Shell Part 1: Metamodel – IDTA Number:
01001-3-0, 2023. [Online]. Verfügbar unter: https://industrialdi-
gitaltwin.org/wp-content/uploads/2023/06/IDTA-01001-3-
0_SpecificationAssetAdministrationShell_Part1_Metamodel.pdf
[6] DIN SPEC 16593 -1:2018-04 RM -SA - Referenzmodell
für Industrie 4.0 Servicearchitekturen - Teil 1: Grundkonzepte ei-
ner interaktionsbasierten Architektur. [Online]. Verfügbar unter:
https://www.dinmedia.de/de/technische-regel/din-spec-16593-
1/287632675
[7] R. Drath u. a., „Diskussionspapier – Interoperabilität
mit der Verwaltungsschale, OPC UA und AutomationML Zielbild
und Handlungsempfehlungen für industrielle Interoperabilität“.
2023. [Online]. Verfügbar unter: https://opcfoundation.org/wp-
content/uploads/2023/04/Diskussionspapier-Zielbild-und-Hand-
lungsempfehlungen-fur-industrielle-Interoperabilitat-5.3-pro-
tected.pdf
[8] DIN SPEC 91345:2016-04:  Referenzarchitekturmodell
Industrie 4.0 (RAMI4.0) . [Online]. Verfügbar unter:
https://www.dinmedia.de/de/technische-regel/din-spec-
91345/250940128
[9] Plattform Industrie 4.0, Hrsg., „Die Verwaltungsscha-
leim Detail von der Idee zum implementierbaren Konzept“. [On-
line]. Verfügbar unter: https://www.plattform -i40.de/IP/Redak-
tion/DE/Downloads/Publikation/verwaltungsschale-im-detail-
präsentation.pdf?__blob=publicationFile&v=1
[10] Gaia-X European Association for Data and Cloud
AISBL, Hrsg., „Gaia -X Architecture Document - 25.05 Release“.
2025. [Online]. Verfügbar unter: https://docs.gaia -x.eu/techni-
cal-committee/architecture-document/25.05/
[11] International Data Spaces Association, Hrsg., „IDS -
RAM V4.2.0“. 2023. [Online]. Verfügbar unter:
https://github.com/International-Data-Spaces-Association/IDS-
RAM_4_0/releases/tag/v4.2.0
[12] P. Koen u. a., „Dataspace Protocol 2025-1“. 2025. Zu-
gegriffen: 14. Oktober 2025. [Online]. Verfügbar unter: https://e-
clipse-dataspace-protocol-base.github.io/DataspaceProto-
col/2025-1/
[13] „Catena-X: Your Automotive Network“. Zugegriffen:
14. Oktober 2025. [Online]. Verfügbar unter: https://catena -
x.net
[14] Eclipse Foundation AISBL, „Data-sharing at scale“. Zu-
gegriffen: 14. Oktober 2025. [Online]. Verfügbar unter: https://e-
clipse-edc.github.io/
[15] M. Sporny, D. Longly, D. Chadwick, und I. Herman,
„Verifiable Credentials Data Model v2.0“. 2025. Zugegriffen: 14.
Oktober 2025. [Online]. Verfügbar unter:
https://www.w3.org/TR/vc-data-model-2.0/
[16] Plattform Industrie 4.0, Hrsg., „Information Model for
Capabilities, Skills & Services - Definition of terminology and pro-
posal for a technology-independent information model for capa-
bilities and skills in flexible manufacturing“. 2022. Zugegriffen:
30. April 2024. [Online]. Verfügbar unter: https://www.platt-
form-i40.de/IP/Redaktion/DE/Downloads/Publikation/Capabili-
tiesSkillsServices.pdf?__blob=publicationFile&v=1
[17] OPC Foundation, „OPC UA for Machinery Standard for
the entire mechanical engineering sector“. Zugegriffen: 14. Ok-
tober 2025. [Online]. Verfügbar unter: https://opcfounda-
tion.org/markets-collaboration/opc-ua-for-machinery/


# Whitepaper_SFKL_Referenzarchitektur

## Seite 15

12

[18] OPC 40001-1: Machinery Basic Building Blocks, 2025.
[Online]. Verfügbar unter: https://reference.opcfounda-
tion.org/Machinery/v104/docs/
[19] VDMA e.V. und Fraunhofer -Institut für Gießerei -,
Composite- und Verarbeitungstechnik IGCV, Hrsg., „Capabilities
and Skills in Production Automation: Consolidating the concept
from the perspective of the mechanical and plant engineering in-
dustry with a focus on OPC UA“. 2022. [Online]. Verfügbar unter:
https://www.vdma.eu/documents/34570/77803117/Capabili-
ties_and_Skills_in_Production_Automation_DE.pdf/9663fef4-
a065-abc6-2d38-687fed93c667?filename=Capabilities_and_Ski-
lls_in_Production_Automation_DE.pdf
[20] Industrial Digital Twin Association, „IDTA 02017 -1-0
Asset Interfaces Description“. 2024. [Online]. Verfügbar unter:
https://github.com/admin-shell-io/submodel-templa-
tes/blob/main/published/Asset%20Interfaces%20Descrip-
tion/1/0/IDTA%2002017-1-0_Submodel_Asset%20Inter-
faces%20Description.pdf
[21] A. Giret und V. Botti, „Holons and agents“, J. Intell.
Manuf., Bd. 15, Nr. 5, S. 645 –659, Okt. 2004, doi:
10.1023/B:JIMS.0000037714.56201.a3.
[22] H. Van Brussel, J. Wyns, P. Valckenaers, L. Bongaerts,
und P. Peeters, „Reference architecture for holonic manufactur-
ing systems: PROSA“, Comput. Ind., Bd. 37, Nr. 3, S. 255 –274,
1998.
[23] S. Jungbluth u. a., „Dynamic Replanning using Multi -
Agent Systems and Asset Administration Shells“, in 2022 IEEE
27th International Conference on Emerging Technologies and
Factory Automation (ETFA), Stuttgart, Germany: IEEE, Sep. 2022,
S. 1–8. doi: 10.1109/ETFA52439.2022.9921716.
[24] A. T. Bernhard u. a., „I4.0 Holonic Multi-agent Testbed
Enabling Shared Production“, in Artificial Intelligence in Manu-
facturing, J. Soldatos, Hrsg., Cham: Springer Nature Switzerland,
2024, S. 231–250. doi: 10.1007/978-3-031-46452-2_13.
[25] OPC 30010: AutoID Devices, 2021. [Online]. Verfügbar
unter: https://reference.opcfoundation.org/AutoID/v101/docs/
[26] „FACTORY-X Das digitale Ökosystem“. Zugegriffen: 14.
Oktober 2025. [Online]. Verfügbar unter: https://factory -
x.org/de/
[27] Factory-X, Hrsg., „MX-Port Concept Enable data shar-
ing across industries“. 2025. [Online]. Verfügbar unter:
https://factory-x.org/wp-content/uploads/MX-Port-Concept-
V1.00-1.pdf
[28] Industrial Digital Twin Association, „Submodel Tem-
plate Repository“. Zugegriffen: 14. Oktober 2025. [Online]. Ver-
fügbar unter: https://smt-repo.admin-shell-io.com/
[29] OPC Foundation, „OPC UA Companion Specifica-
tions“. Zugegriffen: 14. Oktober 2025. [Online]. Verfügbar unter:
https://github.com/OPCFoundation/UA-Nodeset
[30] „Model Contect Protocol Specification“. Zugegriffen:
14. Oktober 2025. [Online]. Verfügbar unter: https://model-
contextprotocol.io/specification/2025-06-18
