// Static React rendering only. The installed Next compiler transpiles two local
// modules in memory; no build output, browser, server or provider is started.
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createRequire } = require("node:module");
// Fail if the already-installed host compiler is absent; never acquire a fallback.
const compilerRequire = createRequire(require.resolve("next/package.json"));
const target = process.platform === "win32" ? `win32-${process.arch}-msvc` : process.platform === "darwin" ? `darwin-${process.arch}` : `linux-${process.arch}-gnu`;
compilerRequire.resolve(`@next/swc-${target}`);
const swc = require("next/dist/build/swc");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

function localModule(file, imports = {}) {
  const code = swc.transformSync(fs.readFileSync(file, "utf8"), { filename:file,
    jsc:{ parser:{syntax:"typescript",tsx:file.endsWith(".tsx")},target:"es2022",transform:{react:{runtime:"automatic"}}},
    module:{type:"commonjs"},
  }).code;
  const module = { exports: {} }, nativeRequire = createRequire(file);
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`, { filename: file })(
    name => Object.hasOwn(imports, name) ? imports[name] : nativeRequire(name), module, module.exports);
  return module.exports;
}
const session = localModule(path.resolve(__dirname, "../app/design-ai/session.ts"));
const Component = localModule(path.resolve(__dirname, "discovery-recommendation.tsx"), { "../app/design-ai/session": session }).default;
const service = {mechanism:"catalogue_service",candidate_id:`service-${"a".repeat(24)}`,label:"Synthetic demand study",
  creation_supported:false,runtime_checked:false,purpose:"Study observations <script>do not execute</script>",
  input_requirements_known:true,required_inputs:[{name:"observations"}],contract_resolution:"resolved",
  steps:[],connection:"Unverified",expected_result_view:[],optional_downloads:[],availability:"Unchecked",limitations:["No registered path"]};
function render(recommendation, busy = false) {
  return renderToStaticMarkup(React.createElement(Component, {recommendation,busy,onCreate:()=>assert.fail("render must not create")}));
}

test("service match renders required information, unchecked runtime and a disabled creation control", () => {
  const html=render(service);
  assert.match(html,/Relevant catalogue capability/);
  assert.match(html,/Required information: observations/);
  assert.match(html,/Runtime availability has not been checked/);
  assert.match(html,/<button[^>]+disabled=""[^>]*>Create this experiment/);
  assert.ok(!html.includes("<script>"));
  assert.match(html,/&lt;script&gt;/);
});

test("unresolved inputs stay unknown rather than being presented as optional", () => {
  const html=render({...service,input_requirements_known:false,required_inputs:[],contract_resolution:"unavailable_or_unsupported"});
  assert.match(html,/Input requirements are unresolved/);
  assert.ok(!html.includes("No required inputs declared"));
});

test("registered recommendation enables explicit Create only when its complete authority is present", () => {
  const item={...service,mechanism:"registered_workflow",candidate_id:`workflow-${"b".repeat(24)}`,creation_supported:true,
    recommendation_revision:"c".repeat(64),recommended_seed:43,steps:[{title:"Generate sample grid",operation:"fixture-generate"}],required_inputs:[{name:"seed"}]};
  assert.match(render(item),/Registered workflow recommendation/);
  assert.ok(!/<button[^>]+disabled/.test(render(item)));
  assert.match(render(item,true),/<button[^>]+disabled/);
  assert.match(render({...item,recommendation_revision:undefined}),/<button[^>]+disabled/);
});
