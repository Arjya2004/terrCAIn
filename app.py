from __future__ import annotations

import streamlit as st

from ai.explanation_generator import generate_explanation
from ai.terrain_planner import plan_terrain
from core.terrain_generator import generate_terrain
from visualization.plotly_terrain import create_terrain_figure
from visualization.terrain_export import heightmap_to_csv_bytes, heightmap_to_png_bytes


st.set_page_config(page_title="terrCAIn", page_icon="🏔️", layout="wide")


def main() -> None:
    st.title("terrCAIn")
    st.subheader("AI-Powered Emergent Terrain Generation using Cellular Automata")
    st.write(
        "Describe a landscape in natural language and generate an emergent 3D terrain using a cellular automata pipeline."
    )

    default_prompt = "Generate a volcanic island"
    user_prompt = st.text_input("Describe your terrain", value=default_prompt)

    if st.button("Generate Terrain", type="primary"):
        with st.spinner("Planning terrain with Azure OpenAI and evolving the automata grid..."):
            planner_result = plan_terrain(user_prompt)
            runtime_preset = planner_result.build_runtime_preset()
            terrain_result = generate_terrain(runtime_preset)
            explanation = generate_explanation(
                prompt=user_prompt,
                planner_result=planner_result,
                preset=runtime_preset,
            )
            figure = create_terrain_figure(
                terrain_result.heightmap,
                title=f"{planner_result.terrain_label} Terrain",
            )

        if planner_result.source == "local_planner":
            st.info(planner_result.status_message)
        elif planner_result.source != "azure_openai":
            st.warning(planner_result.status_message)
        else:
            st.success(planner_result.status_message)

        planner_col, explanation_col = st.columns([1.1, 1.2])

        with planner_col:
            st.markdown("### AI Terrain Planner")
            st.markdown(f"**User Prompt**\n\n{user_prompt}")
            st.markdown(f"**Planner Source**\n\n{planner_result.source_label}")
            st.markdown(f"**Terrain Type**\n\n{planner_result.terrain_label}")
            st.markdown("**AI Interpretation**")
            for item in planner_result.reasoning:
                st.markdown(f"- {item}")
            st.markdown("**Generated Parameters**")
            st.json(planner_result.generated_parameters())

            if planner_result.validation_issues:
                with st.expander("Validation Notes"):
                    for issue in planner_result.validation_issues:
                        st.markdown(f"- {issue}")

        with explanation_col:
            st.markdown("### Terrain Explanation")
            st.write(explanation)

            st.markdown("### Cellular Automata Parameters Used")
            st.json(planner_result.runtime_parameters())

        st.markdown("### Interactive Voxel Terrain")
        st.plotly_chart(figure, use_container_width=True)

        csv_heightmap = heightmap_to_csv_bytes(terrain_result.heightmap)
        png_heightmap = heightmap_to_png_bytes(terrain_result.heightmap)

        st.markdown("### Export Terrain")
        st.write(
            "Export generated terrains for use in game engines, simulations, procedural workflows, and terrain analysis."
        )

        export_csv_col, export_png_col = st.columns(2)

        with export_csv_col:
            st.download_button(
                label="Download CSV Heightmap",
                data=csv_heightmap,
                file_name="terrain_heightmap.csv",
                mime="text/csv",
            )

        with export_png_col:
            st.download_button(
                label="Download PNG Heightmap",
                data=png_heightmap,
                file_name="terrain_heightmap.png",
                mime="image/png",
            )


if __name__ == "__main__":
    main()
