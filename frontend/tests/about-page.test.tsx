import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AboutPage from "@/app/about/page";

describe("About page visual structure", () => {
  it("renders only the mockup sections and the three required Nutrition groups", () => {
    render(<AboutPage />);

    expect(screen.getByRole("heading", { name: "Informasi kesehatan yang lebih mudah dipahami." })).toBeInTheDocument();
    expect(screen.getByText("Fitur utama SEHATIN")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tiga fitur untuk membantu memahami kesehatan" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Nutrition untuk kebutuhan yang berbeda" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Nutrition" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Blood Connect" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Health Checker" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "MPASI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Toddler" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lansia" })).toBeInTheDocument();

    expect(screen.queryByText("Nilai yang kami pegang")).not.toBeInTheDocument();
    expect(screen.queryByText("Tujuan kami")).not.toBeInTheDocument();
    expect(screen.queryByText("Informasi yang jelas, manfaat yang nyata.")).not.toBeInTheDocument();
    expect(screen.queryByText("Membantu lebih banyak orang memahami kesehatannya.")).not.toBeInTheDocument();
  });

  it("keeps the existing destinations for the About page CTAs", () => {
    render(<AboutPage />);

    expect(screen.getByRole("link", { name: /Kenali lebih lanjut/i })).toHaveAttribute("href", "#fitur");
    expect(screen.getByRole("link", { name: /Pelajari lebih lanjut.*Nutrition/i })).toHaveAttribute("href", "/nutrition");
    expect(screen.getByRole("link", { name: /Pelajari lebih lanjut.*Blood Connect/i })).toHaveAttribute("href", "/blood");
    expect(screen.getByRole("link", { name: /Pelajari lebih lanjut.*Health Checker/i })).toHaveAttribute("href", "/health-checker");
    expect(screen.getByRole("link", { name: /Lihat semua fitur Nutrition/i })).toHaveAttribute("href", "/nutrition");
  });
});
