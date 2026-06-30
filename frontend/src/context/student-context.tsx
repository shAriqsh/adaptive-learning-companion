"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { createStudent, getStudents } from "@/lib/api";
import type { Student } from "@/lib/types";

interface StudentContextValue {
  students: Student[];
  activeStudent: Student | null;
  setActiveStudent: (student: Student) => void;
  addStudent: (name: string, email?: string) => Promise<Student>;
  loading: boolean;
}

const StudentContext = createContext<StudentContextValue | null>(null);

export function StudentProvider({ children }: { children: ReactNode }) {
  const [students, setStudents] = useState<Student[]>([]);
  const [activeStudent, setActiveStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState(true);

  // Load students on mount
  useEffect(() => {
    getStudents()
      .then((list) => {
        setStudents(list);
        // Auto-select the first student if available
        if (list.length > 0 && !activeStudent) {
          setActiveStudent(list[0]);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addStudent = useCallback(
    async (name: string, email?: string) => {
      const student = await createStudent({ name, email });
      setStudents((prev) => [...prev, student]);
      setActiveStudent(student);
      return student;
    },
    []
  );

  return (
    <StudentContext.Provider
      value={{ students, activeStudent, setActiveStudent, addStudent, loading }}
    >
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent() {
  const ctx = useContext(StudentContext);
  if (!ctx) throw new Error("useStudent must be used within StudentProvider");
  return ctx;
}
