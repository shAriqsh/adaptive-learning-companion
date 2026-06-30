import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChatInput } from "@/components/chat/chat-input";

describe("ChatInput Component", () => {
  it("renders a textarea and a send button", () => {
    render(<ChatInput onSend={vi.fn()} />);
    expect(screen.getByPlaceholderText(/Ask me anything/i)).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("calls onSend with the trimmed message when clicking send", () => {
    const handleSend = vi.fn();
    render(<ChatInput onSend={handleSend} />);
    
    const textarea = screen.getByPlaceholderText(/Ask me anything/i);
    const button = screen.getByRole("button");

    fireEvent.change(textarea, { target: { value: "   Hello World!   " } });
    fireEvent.click(button);

    expect(handleSend).toHaveBeenCalledWith("Hello World!");
    expect(textarea).toHaveValue(""); // should clear input
  });

  it("does not call onSend if the input is empty or only whitespace", () => {
    const handleSend = vi.fn();
    render(<ChatInput onSend={handleSend} />);
    
    const textarea = screen.getByPlaceholderText(/Ask me anything/i);
    const button = screen.getByRole("button");

    fireEvent.change(textarea, { target: { value: "     " } });
    fireEvent.click(button);

    expect(handleSend).not.toHaveBeenCalled();
  });

  it("calls onSend when pressing Enter", () => {
    const handleSend = vi.fn();
    render(<ChatInput onSend={handleSend} />);
    
    const textarea = screen.getByPlaceholderText(/Ask me anything/i);

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", shiftKey: false });

    expect(handleSend).toHaveBeenCalledWith("Test message");
  });

  it("disables input and button when disabled prop is true", () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);
    
    expect(screen.getByPlaceholderText(/Ask me anything/i)).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
