import { describe, expect, it } from "vitest";
import { mealVisualAsset } from "@/components/nutrition-visuals";
import { formatMenuDisplayTitle } from "@/lib/nutrition-menu-presentation";

describe("nutrition daily menu visual mapping", () => {
  it("maps MPASI pumpkin menu to the pumpkin visual", () => {
    expect(mealVisualAsset("mpasi", "Bubur nasi kental dengan ayam matang yang dilumat, labu, dan sedikit minyak.")).toContain("mpasi-pumpkin-veg");
  });

  it("maps toddler protein menu to a toddler main-meal visual", () => {
    expect(mealVisualAsset("toddler", "Nasi dengan telur matang, sayur, dan buah.")).toContain("toddler-main");
  });

  it("maps elderly fish menu to the fish meal visual", () => {
    expect(mealVisualAsset("elderly", "Makan utama berupa nasi, ikan matang, sayur bening, dan buah.")).toContain("elderly-fish");
  });

  it("prefers an explicit backend visual key when available", () => {
    expect(mealVisualAsset("elderly", "Menu lain", "elderly_soft")).toContain("elderly-soft");
  });

  it("uses the egg-and-greens MPASI illustration even when an old generic visual key says vegetable", () => {
    expect(
      mealVisualAsset(
        "mpasi",
        "Bubur beras dengan telur matang yang dilumat, bayam, dan sedikit minyak.",
        "mpasi_vegetable",
      ),
    ).toContain("mpasi-rice-egg-spinach");
  });

  it("maps toddler fruit-and-yogurt snack to the yogurt illustration", () => {
    expect(
      mealVisualAsset(
        "toddler",
        "Camilan berupa buah potong sesuai kemampuan makan dan yogurt tawar.",
        "toddler_fruit",
      ),
    ).toContain("toddler-fruit-yogurt");
  });

  it("maps toddler fish meals to a fish illustration instead of the generic protein tray", () => {
    expect(
      mealVisualAsset(
        "toddler",
        "Makan utama berupa nasi, ikan matang tanpa duri, tempe, dan sayur.",
        "toddler_protein",
      ),
    ).toContain("toddler-fish-vegetable");
  });

  it("maps elderly oatmeal breakfast to the breakfast illustration despite a generic protein key", () => {
    expect(
      mealVisualAsset(
        "elderly",
        "Sarapan berupa oatmeal, telur matang, dan buah.",
        "elderly_protein",
      ),
    ).toContain("elderly-breakfast-new");
  });
});


describe("nutrition menu presentation", () => {
  it("removes raw separators from stored menu titles", () => {
    const title = formatMenuDisplayTitle("mpasi", "Bubur Ayam + Sayur : MPASI");
    expect(title).toBe("Bubur Ayam dengan Sayur.");
    expect(title).not.toContain("+");
    expect(title).not.toContain(":");
  });

  it("keeps context notes out of the large elderly menu title", () => {
    const title = formatMenuDisplayTitle("elderly", "Makan utama: nasi + ikan matang + sayur bening + buah Catatan konteks: kurangi minyak");
    expect(title).toBe("Makan utama berupa nasi, ikan matang, sayur bening, dan buah.");
  });

  it("maps the same menu deterministically to the same visual", () => {
    const menu = "Camilan berupa buah dan oat.";
    expect(mealVisualAsset("toddler", menu)).toBe(mealVisualAsset("toddler", menu));
  });
});
