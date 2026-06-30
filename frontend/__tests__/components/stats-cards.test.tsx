import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatsCards } from "@/components/dashboard/stats-cards";

describe("StatsCards Component", () => {
  it("renders empty states when summary is null", () => {
    render(<StatsCards summary={null} />);
    
    expect(screen.getByText("Total Sessions")).toBeInTheDocument();
    expect(screen.getByText("Overall Mastery")).toBeInTheDocument();
    expect(screen.getByText("Strongest Skill")).toBeInTheDocument();
    expect(screen.getByText("Weakest Skill")).toBeInTheDocument();
    
    // Values should be dashes
    const dashes = screen.getAllByText("—");
    expect(dashes).toHaveLength(4);
  });

  it("renders formatted values when summary is provided", () => {
    const summary = {
      total_sessions: 42,
      overall_mastery: 85.5,
      strongest_skill: "Calculus",
      weakest_skill: "Algebra",
      topics_studied: ["Calculus", "Algebra"],
      mastery_data: []
    };

    render(<StatsCards summary={summary} />);
    
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("85.5%")).toBeInTheDocument();
    expect(screen.getByText("Calculus")).toBeInTheDocument();
    expect(screen.getByText("Algebra")).toBeInTheDocument();
  });
});
