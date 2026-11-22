import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import TagInput from "../components/TagInput";
import RankingTable from "../components/RankingTable";
import { ScoreBadge, StatusPill } from "../components/ui";
import { errorMessage } from "../api/client";
import { fmtScore, scoreTone, validateFile } from "../utils/format";

describe("format utils", () => {
  it("formats scores and tones", () => {
    expect(fmtScore(72.345)).toBe("72.3");
    expect(fmtScore(null)).toBe("—");
    expect(scoreTone(80)).toBe("emerald");
    expect(scoreTone(40)).toBe("amber");
  });

  it("validates files on the client", () => {
    expect(validateFile(new File(["x"], "cv.txt"))).toMatch(/Unsupported/);
    expect(validateFile(new File([], "cv.pdf"))).toMatch(/empty/);
    expect(validateFile(new File(["%PDF"], "cv.pdf"))).toBeNull();
  });

  it("builds readable API error messages", () => {
    expect(errorMessage({ response: { status: 404, data: { detail: "Job 9 not found" } } })).toBe("Job 9 not found");
    expect(errorMessage({ response: { status: 422, data: { errors: [{ field: "raw_text", message: "too short" }] } } }))
      .toBe("raw_text: too short");
    expect(errorMessage({ request: {} })).toMatch(/Cannot reach/);
  });
});

describe("components", () => {
  it("TagInput adds and removes tags", () => {
    const onChange = vi.fn();
    render(<TagInput label="Skills" value={["Python"]} onChange={onChange} />);
    const input = screen.getByLabelText("Skills");
    fireEvent.change(input, { target: { value: "SQL, python" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["Python", "SQL"]); // case-insensitive de-duplication
    fireEvent.click(screen.getByLabelText("Remove Python"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("ScoreBadge and StatusPill render", () => {
    render(<><ScoreBadge score={81.25} /><StatusPill status="pending_analysis" /></>);
    expect(screen.getByText("81.3%")).toBeInTheDocument();
    expect(screen.getByText("Pending analysis")).toBeInTheDocument();
  });

  it("RankingTable renders rows, sorting and selection", () => {
    const rows = [
      { resume_id: 1, candidate_id: 10, rank: 1, name: "Aarav Mehta", email: "a@example.com", filename: "a.pdf",
        experience_years: 6, final_score: 91.2, fit_label: "Strong match", matched_skills: ["Python", "FastAPI"],
        missing_skills: ["React"], status: "analyzed" },
      { resume_id: 2, candidate_id: null, rank: null, name: null, email: null, filename: "broken.pdf",
        experience_years: null, final_score: null, fit_label: null, matched_skills: [], missing_skills: [],
        status: "failed", error: "Corrupted PDF" },
    ];
    const onSort = vi.fn(), onToggle = vi.fn(), onOpen = vi.fn();
    render(<MemoryRouter><RankingTable rows={rows} sort={{ by: "rank", order: "asc" }} onSort={onSort}
      selected={[]} onToggle={onToggle} onOpen={onOpen} /></MemoryRouter>);
    expect(screen.getByText("Aarav Mehta")).toBeInTheDocument();
    expect(screen.getByText("Corrupted PDF")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Match"));
    expect(onSort).toHaveBeenCalledWith("final_score");
    fireEvent.click(screen.getByLabelText("Select Aarav Mehta for comparison"));
    expect(onToggle).toHaveBeenCalledWith(10);
    fireEvent.click(screen.getByText("Aarav Mehta"));
    expect(onOpen).toHaveBeenCalled();
  });
});
