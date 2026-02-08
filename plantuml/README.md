PlantUML diagrams for the NERO project

Files:
- system_overview.puml — high-level system overview (client, server, DB, external services)
- c4_context.puml — C4-style context diagram (uses C4-PlantUML include)
- deployment.puml — deployment/network diagram with ports and components

Render locally with PlantUML (two options):

1) Using Docker (recommended if you don't have Java/PlantUML installed):

```bash
# from project root
docker run --rm -v "$PWD/plantuml":/workspace plantuml/plantuml -tpng /workspace/system_overview.puml
docker run --rm -v "$PWD/plantuml":/workspace plantuml/plantuml -tsvg /workspace/system_overview.puml

# render all .puml files to PNG
for f in plantuml/*.puml; do docker run --rm -v "$PWD/plantuml":/workspace plantuml/plantuml -tpng "/workspace/$(basename "$f")"; done
```

2) Using plantuml.jar (requires Java):

```bash
# download plantuml.jar once
wget https://github.com/plantuml/plantuml/releases/download/v1.2024.21/plantuml.jar -O plantuml.jar
# render PNG
java -jar plantuml.jar -tpng plantuml/system_overview.puml
# render SVG
java -jar plantuml.jar -tsvg plantuml/system_overview.puml
```

Notes & options:
- `c4_context.puml` uses the C4-PlantUML include; rendering requires internet access to fetch the include, or you can download the C4 library locally and adjust the `!include` path.
- If you run into TLS or network restrictions when using the `!include`, update the include to a local path by downloading the file from https://github.com/plantuml-stdlib/C4-PlantUML
- To produce a single combined diagram image for documentation, render each `.puml` to SVG and embed them in your docs.

If you want, I can try to render PNG/SVG here and attach them — do you want me to attempt rendering locally and add the generated images into the repository? If yes, I will attempt to run PlantUML in this environment and commit the images.