import denmarkConfigAssistant from "../../../../examples/workshop-service-manifests/denmark-config-assistant.json";
import germanyDataProvider from "../../../../examples/workshop-service-manifests/germany-data-provider.json";
import dutchGridSynth from "../../../../examples/workshop-service-manifests/dutch-grid-synth.json";
import portugalDataLoader from "../../../../examples/workshop-service-manifests/portugal-data-loader.json";

export type WorkshopExample = {
  key: string;
  country: string;
  service: string;
  sourceUrl: string;
  revision: string;
  manifestPath: string;
  manifest: Record<string, unknown>;
};

const wp3Revision = "e8914565e966a2d78879c314f980574769d31b87";

export const workshopExamples: WorkshopExample[] = [
  {
    key: "germany",
    country: "Germany",
    service: "ProvideData",
    sourceUrl: "https://github.com/AI-EFFECT/ai-effect-wp3",
    revision: wp3Revision,
    manifestPath: "use-cases/germany-node/export/blueprint.json#data_provider1",
    manifest: germanyDataProvider,
  },
  {
    key: "portugal",
    country: "Portugal",
    service: "ExecuteQuery",
    sourceUrl: "https://github.com/AI-EFFECT/ai-effect-wp3",
    revision: wp3Revision,
    manifestPath: "use-cases/portugal-node-integrated/export/blueprint.json#data_loader1",
    manifest: portugalDataLoader,
  },
  {
    key: "denmark",
    country: "Denmark",
    service: "BuildRunConfig",
    sourceUrl: "https://github.com/AI-EFFECT/ai-effect-wp3",
    revision: wp3Revision,
    manifestPath: "use-cases/denmark-node/connections.json#config_assistant",
    manifest: denmarkConfigAssistant,
  },
  {
    key: "dutch",
    country: "Dutch",
    service: "ConfigureAndSynthesize",
    sourceUrl: "https://github.com/paulban/ai-effect-wp3",
    revision: "ba598b2459f9986dac4e37dcc5d7d3298f25dc3a",
    manifestPath: "use-cases/dutch_node/data_synthesizer/docker-compose-all.yml#synthetic-data",
    manifest: dutchGridSynth,
  },
];
