"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "@dagrejs/dagre";
import type { SkillNode } from "@/lib/types";

// ── Color helpers ────────────────────────────────────────────────────────

function getMasteryColor(score: number) {
  if (score >= 70) return { bg: "bg-emerald-500/20", border: "border-emerald-500/40", text: "text-emerald-400", dot: "#34d399" };
  if (score >= 40) return { bg: "bg-amber-500/20", border: "border-amber-500/40", text: "text-amber-400", dot: "#fbbf24" };
  return { bg: "bg-rose-500/20", border: "border-rose-500/40", text: "text-rose-400", dot: "#f87171" };
}

function getMasteryHex(score: number): string {
  if (score >= 70) return "#34d399";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
}

// ── Custom Node Component ────────────────────────────────────────────────

interface SkillNodeData {
  label: string;
  mastery: number;
  isRoot: boolean;
  [key: string]: unknown;
}

function SkillNodeComponent({ data }: { data: SkillNodeData }) {
  const colors = getMasteryColor(data.mastery);

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-none" />
      <div
        className={`rounded-xl border ${colors.border} ${colors.bg} px-4 py-3 shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-105`}
        style={{ minWidth: data.isRoot ? 160 : 130 }}
      >
        <p className={`text-center text-xs font-semibold ${data.isRoot ? "text-violet-300" : "text-gray-200"}`}>
          {data.label}
        </p>
        <div className="mt-2 flex items-center justify-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${data.mastery}%`,
                backgroundColor: colors.dot,
              }}
            />
          </div>
          <span className={`text-[10px] font-bold ${colors.text}`}>
            {data.mastery.toFixed(0)}%
          </span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-none" />
    </>
  );
}

const nodeTypes: NodeTypes = {
  skillNode: SkillNodeComponent,
};

// ── Layout with dagre ────────────────────────────────────────────────────

const NODE_WIDTH = 150;
const NODE_HEIGHT = 70;

function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 80 });

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
}

// ── Flatten recursive tree ───────────────────────────────────────────────

function flattenTree(
  tree: SkillNode[],
  parentId?: string
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function walk(node: SkillNode, parent?: string) {
    const id = String(node.id);
    nodes.push({
      id,
      type: "skillNode",
      position: { x: 0, y: 0 },
      data: {
        label: node.name,
        mastery: node.mastery_score,
        isRoot: !parent,
      },
    });

    if (parent) {
      edges.push({
        id: `e-${parent}-${id}`,
        source: parent,
        target: id,
        style: { stroke: getMasteryHex(node.mastery_score), strokeWidth: 2, opacity: 0.6 },
        animated: node.mastery_score > 0,
      });
    }

    node.children?.forEach((child) => walk(child, id));
  }

  tree.forEach((root) => walk(root, parentId));
  return { nodes, edges };
}

// ── Main Component ───────────────────────────────────────────────────────

interface SkillTreeProps {
  tree: SkillNode[];
  onNodeClick?: (node: SkillNode) => void;
}

export function SkillTree({ tree, onNodeClick }: SkillTreeProps) {
  const { rawNodes, rawEdges } = useMemo(() => {
    const { nodes, edges } = flattenTree(tree);
    return { rawNodes: nodes, rawEdges: edges };
  }, [tree]);

  const layoutedNodes = useMemo(
    () => layoutGraph(rawNodes, rawEdges),
    [rawNodes, rawEdges]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(rawEdges);

  // Update when tree data changes
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = flattenTree(tree);
    const laid = layoutGraph(newNodes, newEdges);
    setNodes(laid);
    setEdges(newEdges);
  }, [tree, setNodes, setEdges]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (!onNodeClick) return;
      // Find the original SkillNode
      function findNode(nodes: SkillNode[], id: number): SkillNode | null {
        for (const n of nodes) {
          if (n.id === id) return n;
          const found = findNode(n.children ?? [], id);
          if (found) return found;
        }
        return null;
      }
      const skill = findNode(tree, parseInt(node.id));
      if (skill) onNodeClick(skill);
    },
    [tree, onNodeClick]
  );

  return (
    <div className="h-full w-full rounded-xl border border-white/10 bg-gray-900/40">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="rgba(139, 92, 246, 0.05)" gap={20} />
        <Controls
          className="!border-white/10 !bg-gray-900/80 !rounded-lg [&>button]:!bg-gray-800 [&>button]:!border-white/10 [&>button]:!text-gray-400 [&>button:hover]:!bg-gray-700"
        />
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as SkillNodeData;
            return getMasteryHex(data?.mastery ?? 0);
          }}
          maskColor="rgba(3, 7, 18, 0.7)"
          style={{ background: "rgba(3, 7, 18, 0.8)" }}
        />
      </ReactFlow>
    </div>
  );
}
