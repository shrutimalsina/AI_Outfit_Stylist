const select = document.querySelector("#query");
const status = document.querySelector("#status");
const matches = document.querySelector("#matches");

try {
  const response = await fetch("./examples.json");
  if (!response.ok) throw new Error("Examples unavailable");
  const examples = await response.json();
  function render() {
    const example = examples[Number(select.value)];
    status.textContent = "Saved recommendations";
    matches.replaceChildren(...example.matches.map(match => {
      const item = document.createElement("li");
      item.textContent = `${match.category} · cosine similarity ${match.similarity.toFixed(3)}`;
      return item;
    }));
  }
  examples.forEach((example, index) => select.add(new Option(example.label, index)));
  select.disabled = false;
  select.addEventListener("change", render);
  render();
} catch {
  status.textContent = "Examples could not be loaded. Try refreshing the page.";
}
