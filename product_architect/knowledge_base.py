import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class KnowledgeChunk:
    id: str
    category: str
    source: str
    content: str
    metadata: Dict[str, Any]

class KnowledgeBase:
    """
    Lightweight knowledge base for architecture domain knowledge.
    For production: replace with FAISS + embeddings for semantic search.
    Current implementation: keyword-based retrieval (works without GPU).
    """
    
    def __init__(self, kb_path: Optional[str] = None):
        if kb_path is None:
            # Default to adjacent knowledge_base directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.kb_path = os.path.join(base_dir, "knowledge_base")
        else:
            self.kb_path = kb_path
            
        self.chunks: List[KnowledgeChunk] = []
        self._load()
    
    def _load(self):
        """Load all knowledge chunks from the KB directory."""
        if not os.path.exists(self.kb_path):
            self._create_default_kb()
            return
        
        for fname in sorted(os.listdir(self.kb_path)):
            if fname.endswith('.json'):
                fp = os.path.join(self.kb_path, fname)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                self.chunks.append(KnowledgeChunk(**item))
                except Exception as e:
                    print(f"Warning: failed to load {fp}: {e}")
                    
        if not self.chunks:
            self._create_default_kb()
    
    def _create_default_kb(self):
        """Create default knowledge base with hardcoded NVIDIA-level data."""
        default_kb = self._get_default_knowledge()
        os.makedirs(self.kb_path, exist_ok=True)
        
        for category, chunks in default_kb.items():
            out_file = os.path.join(self.kb_path, f"{category}.json")
            with open(out_file, 'w', encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)
            for c in chunks:
                self.chunks.append(KnowledgeChunk(**c))
    
    def retrieve(self, query: str, categories: List[str] = None, 
                 top_k: int = 5) -> List[KnowledgeChunk]:
        """Retrieve relevant knowledge chunks."""
        query_terms = set(query.lower().split())
        scored = []
        
        for chunk in self.chunks:
            if categories and chunk.category not in categories:
                continue
            content_terms = set(chunk.content.lower().split())
            overlap = len(query_terms & content_terms)
            if overlap > 0:
                scored.append((overlap, chunk))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]
    
    def get_context(self, query: str, categories: List[str] = None) -> str:
        """Get formatted context string for LLM prompts."""
        chunks = self.retrieve(query, categories, top_k=8)
        if not chunks:
            return ""
        
        context = "\n\n=== RELEVANT DOMAIN KNOWLEDGE ===\n"
        for i, chunk in enumerate(chunks):
            context += f"\n[{i+1}] {chunk.category} (source: {chunk.source}):\n{chunk.content}\n"
        context += "\n=== END DOMAIN KNOWLEDGE ===\n\n"
        return context
    
    def _get_default_knowledge(self) -> Dict[str, List[Dict]]:
        """NVIDIA-caliber default knowledge base."""
        return {
            "nvidia_architecture": [
                {
                    "id": "arch_blackwell_001",
                    "category": "nvidia_architecture",
                    "source": "NVIDIA Blackwell Architecture Whitepaper",
                    "content": """Blackwell GPU Architecture:
- 5th-generation Tensor Cores with NVFP4 support
- 208B transistors across two reticle-limited dies
- TSMC 4NP custom process node
- HBM3e memory: up to 192GB at 8 TB/s bandwidth
- NVLink 5.0: 1.8 TB/s bidirectional, 100 Gbps/lane
- 192 MB L2 cache with 50x capacity compression
- 1000W TDP for B200 SXM module
- 25x energy efficiency improvement over Hopper per AI operation
- Dual-die chiplet design on CoWoS-L packaging""",
                    "metadata": {"generation": "blackwell", "year": 2024}
                },
                {
                    "id": "arch_hopper_001",
                    "category": "nvidia_architecture",
                    "source": "NVIDIA Hopper Architecture Whitepaper",
                    "content": """Hopper H100 GPU Architecture:
- 4th-generation Tensor Cores with FP8 Transformer Engine
- 80B transistors, 814 mm² die, TSMC 4N process
- HBM3 memory: 80GB at 3.35 TB/s bandwidth
- NVLink 4.0: 900 GB/s bidirectional
- 50 MB L2 cache
- 700W TDP for SXM module
- 132 SMs, 16,896 FP32 CUDA cores
- 256 KB register file per SM, 228 KB L1/shared memory per SM""",
                    "metadata": {"generation": "hopper", "year": 2022}
                },
                {
                    "id": "arch_ampere_001",
                    "category": "nvidia_architecture",
                    "source": "NVIDIA Ampere Architecture Whitepaper",
                    "content": """Ampere A100 GPU Architecture:
- 3rd-generation Tensor Cores with TF32, BF16, FP16, INT8, INT4
- 54B transistors, 826 mm² die, TSMC 7N process
- HBM2e memory: 40GB/80GB at 1.55/2.0 TB/s
- NVLink 3.0: 600 GB/s bidirectional
- 40 MB L2 cache
- 400W TDP for SXM4
- 108 SMs, 6,912 FP32 CUDA cores
- MIG (Multi-Instance GPU): up to 7 instances""",
                    "metadata": {"generation": "ampere", "year": 2020}
                },
                {
                    "id": "arch_sm_design_001",
                    "category": "nvidia_architecture",
                    "source": "NVIDIA SM Architecture Analysis",
                    "content": """NVIDIA Streaming Multiprocessor (SM) Evolution:
- Turing/Ada: 4 processing blocks per SM, each with 32 FP32 cores, 1 warp scheduler
- Hopper: 4 sub-partitions per SM, each with 32 FP32 cores, 1 warp scheduler, 1 Tensor Core
- Register file: 256 KB per SM (Hopper), 64K × 32-bit registers
- L1/Shared memory: configurable, up to 228 KB on Hopper
- Warp size: 32 threads
- Key SM design principles: maximize thread-level parallelism, hide memory latency through context switching, balance compute and memory resources""",
                    "metadata": {"component": "sm"}
                }
            ],
            "process_node_data": [
                {
                    "id": "node_tsmc_3nm",
                    "category": "process_node_data",
                    "source": "TSMC Public Data + Industry Analysis",
                    "content": """TSMC 3nm (N3E/N3P) Process:
- Wafer cost: ~$20,000
- Mask cost (full set): ~$6-8M
- Defect density: ~0.20-0.25 defects/cm²
- Transistor density: ~1.7x N5
- Performance: ~1.1x N5 at same power, or ~0.5x power at same speed
- Minimum pitch: FinFET, contacted poly pitch ~45nm
- Reticle limit: 858 mm² (33mm × 26mm)
- Availability: High volume production 2024+""",
                    "metadata": {"node": "3nm", "foundry": "tsmc"}
                },
                {
                    "id": "node_tsmc_4nm",
                    "category": "process_node_data",
                    "source": "TSMC Public Data + Industry Analysis",
                    "content": """TSMC 4nm (N4/N4P/N4X) Process:
- Wafer cost: ~$16,000
- Mask cost (full set): ~$4-5M
- Defect density: ~0.28-0.32 defects/cm²
- Transistor density: ~1.2x N5
- Performance: ~1.07x N5 at same power
- NVIDIA 4NP: custom variant for GPU workloads
- Reticle limit: 858 mm²
- Availability: High volume production 2023+""",
                    "metadata": {"node": "4nm", "foundry": "tsmc"}
                },
                {
                    "id": "node_tsmc_5nm",
                    "category": "process_node_data",
                    "source": "TSMC Public Data + Industry Analysis",
                    "content": """TSMC 5nm (N5/N5P) Process:
- Wafer cost: ~$10,000
- Mask cost (full set): ~$3.5-4.7M
- Defect density: ~0.32-0.38 defects/cm²
- Transistor density: ~1.8x N7
- Performance: ~1.15x N7 at same power, or ~0.7x power at same speed
- Reticle limit: 858 mm²
- Availability: High volume production 2020+""",
                    "metadata": {"node": "5nm", "foundry": "tsmc"}
                }
            ],
            "hbm_specs": [
                {
                    "id": "hbm_hbm4",
                    "category": "hbm_specs",
                    "source": "JEDEC + SK Hynix + Industry Analysis",
                    "content": """HBM4 Memory Specification:
- Data rate: 6.4 Gbps/pin (target), up to 8.0 Gbps/pin
- Bandwidth per stack: ~1.6 TB/s (12-high, 2048-bit)
- Capacity per stack: 36GB (12-high), 48GB (16-high)
- I/O voltage: 1.1V
- Power efficiency: ~30% better than HBM3e
- Availability: 2026 sampling, 2027 HVM
- Key features: Lower power, higher bandwidth, ECC support""",
                    "metadata": {"generation": "hbm4"}
                },
                {
                    "id": "hbm_hbm3e",
                    "category": "hbm_specs",
                    "source": "JEDEC + SK Hynix + Industry Analysis",
                    "content": """HBM3e Memory Specification:
- Data rate: 8.0 Gbps/pin
- Bandwidth per stack: ~1.0 TB/s (12-high, 1024-bit)
- Capacity per stack: 24GB (12-high), 16GB (8-high)
- I/O voltage: 1.1V
- Stack height: 8-high or 12-high
- Availability: High volume production 2024+
- Used in: NVIDIA Blackwell B200""",
                    "metadata": {"generation": "hbm3e"}
                },
                {
                    "id": "hbm_hbm3",
                    "category": "hbm_specs",
                    "source": "JEDEC + SK Hynix + Industry Analysis",
                    "content": """HBM3 Memory Specification:
- Data rate: 6.4 Gbps/pin
- Bandwidth per stack: ~819 GB/s (12-high, 1024-bit)
- Capacity per stack: 16GB (8-high), 24GB (12-high)
- I/O voltage: 1.1V
- Stack height: 8-high or 12-high
- Availability: High volume production 2022+
- Used in: NVIDIA Hopper H100""",
                    "metadata": {"generation": "hbm3"}
                }
            ],
            "workload_characteristics": [
                {
                    "id": "wl_llm_training",
                    "category": "workload_characteristics",
                    "source": "NVIDIA Analysis + Academic Papers",
                    "content": """LLM Training Workload Characteristics:
- Arithmetic intensity: ~3-5 FLOPs/byte (moderate)
- Dominant operation: Matrix multiplication (GEMM)
- Batch sizes: Large (256-4096)
- Sequence lengths: 4K-128K tokens
- Precision: Mixed precision (FP16/BF16 with FP32 accumulation)
- Bottleneck: Balanced between compute and memory for large batches
- Tensor Core utilization: High (80-95%) for well-optimized kernels
- Communication: Heavy all-reduce, all-gather, reduce-scatter in distributed training
- Key architectural needs: High FP16/BF16 compute, high memory bandwidth, fast interconnect (NVLink)""",
                    "metadata": {"workload": "llm_training"}
                },
                {
                    "id": "wl_llm_inference_decode",
                    "category": "workload_characteristics",
                    "source": "NVIDIA Analysis + Industry Benchmarks",
                    "content": """LLM Autoregressive Decode (Inference) Characteristics:
- Arithmetic intensity: ~0.5-1.5 FLOPs/byte (VERY LOW)
- CRITICAL INSIGHT: Operates at ~1 FLOP per byte of memory traffic
- This is SEVERELY memory-bound on all modern GPUs
- Dominant operation: Matrix-vector multiplication (GEMV), not GEMM
- Tensor Core utilization: VERY LOW (often <10%) because shapes don't match
- Batch sizes: Small to medium (1-256) for interactive use
- Precision: FP8, INT8, INT4 for throughput
- Bottleneck: HBM bandwidth is the primary constraint
- Key architectural needs: EXTREME memory bandwidth, large on-chip caches, efficient low-precision formats, KV cache management
- Roofline: Ridge point of H100 is ~295 FLOPs/byte; decode at ~1 FLOP/byte uses only ~0.3% of peak compute""",
                    "metadata": {"workload": "llm_inference_decode"}
                },
                {
                    "id": "wl_llm_prefill",
                    "category": "workload_characteristics",
                    "source": "NVIDIA Analysis + Industry Benchmarks",
                    "content": """LLM Prefill Phase Characteristics:
- Arithmetic intensity: ~10-20 FLOPs/byte
- Dominant operation: Matrix-matrix multiplication (GEMM) on prompt tokens
- Tensor Core utilization: High (70-90%)
- Precision: FP8, FP16, BF16
- Bottleneck: Compute-bound for long sequences
- Key architectural needs: High compute throughput, good FP8/FP16 performance""",
                    "metadata": {"workload": "llm_prefill"}
                },
                {
                    "id": "wl_diffusion",
                    "category": "workload_characteristics",
                    "source": "NVIDIA Analysis",
                    "content": """Diffusion Model Workload Characteristics:
- Arithmetic intensity: ~5-10 FLOPs/byte
- Dominant operations: Convolutions, attention, GEMMs
- Precision: FP16, BF16, FP8
- Tensor Core utilization: Moderate to high
- Bottleneck: Balanced, shifts with image resolution
- Key architectural needs: Good FP16 compute, memory bandwidth, attention acceleration""",
                    "metadata": {"workload": "diffusion"}
                }
            ],
            "interface_standards": [
                {
                    "id": "if_pcie6",
                    "category": "interface_standards",
                    "source": "PCI-SIG",
                    "content": """PCIe Gen 6 Specification:
- Data rate: 64 GT/s per lane (PAM4 encoding)
- Bandwidth per lane: ~8 GB/s bidirectional
- x16 slot: ~128 GB/s bidirectional
- CXL 3.1 support
- Forward error correction (FEC)
- Availability: 2025+""",
                    "metadata": {"interface": "pcie_gen6"}
                },
                {
                    "id": "if_nvlink5",
                    "category": "interface_standards",
                    "source": "NVIDIA",
                    "content": """NVLink 5.0 Specification:
- Data rate: 100 Gbps per lane (PAM4)
- 18 lanes per link
- Bandwidth: 1.8 TB/s bidirectional per GPU
- Latency: ~50 ns
- 8-way multi-GPU support within node
- Switch-based scaling for larger systems
- Error correction, retransmission, flow control""",
                    "metadata": {"interface": "nvlink5"}
                },
                {
                    "id": "if_cxl3",
                    "category": "interface_standards",
                    "source": "CXL Consortium",
                    "content": """CXL 3.0/3.1 Specification:
- Built on PCIe Gen 6 PHY
- CXL.io, CXL.cache, CXL.mem protocols
- Memory pooling, sharing, expansion
- Fabric capabilities for multi-host
- Latency: ~100-200 ns
- Key use case: Disaggregated memory in AI datacenters""",
                    "metadata": {"interface": "cxl3"}
                }
            ],
            "cost_models": [
                {
                    "id": "cost_wafer_2026",
                    "category": "cost_models",
                    "source": "Industry Analysis + Foundry Pricing",
                    "content": """Wafer Costs (2026 estimates):
- TSMC 2nm: ~$30,000 per wafer
- TSMC 3nm (N3P): ~$20,000 per wafer
- TSMC 4nm (N4P): ~$16,000 per wafer
- TSMC 5nm (N5P): ~$10,000 per wafer
- TSMC 7nm: ~$6,000 per wafer

Mask Costs (full set):
- 2nm: ~$10M+
- 3nm: ~$6-8M
- 5nm: ~$3.5-4.7M
- 7nm: ~$2-2.5M

Packaging Costs:
- CoWoS-L with HBM3e: ~$800-1200 per unit
- CoWoS-S with HBM3: ~$500-800 per unit
- SXM substrate: ~$200-400
- HBM stacks: ~$15-20 per GB (HBM3e)""",
                    "metadata": {"year": 2026}
                }
            ],
            "power_models": [
                {
                    "id": "power_gpu_allocation",
                    "category": "power_models",
                    "source": "NVIDIA Analysis + Die Shots",
                    "content": """Typical High-End GPU Power Budget Allocation (1000W TDP):
- Compute cores (SM array): 40-50% (400-500W)
  - CUDA cores, Tensor Cores, register files, schedulers
- Memory PHY + Controllers: 20-25% (200-250W)
  - HBM PHYs, memory controllers, PHY PLLs
- L2 Cache: 10-15% (100-150W)
  - SRAM arrays, access logic
- NoC/Interconnect: 8-12% (80-120W)
  - On-chip network, crossbars, buffers
- NVLink/PCIe PHYs: 8-12% (80-120W)
  - High-speed SerDes, PLLs, transmitters/receivers
- Clock generation & distribution: 3-5% (30-50W)
  - PLLs, clock trees, buffers
- Power management & thermal: 2-3% (20-30W)
  - Sensors, controllers, I2C logic

Power density: High-end GPU compute regions can reach 3-5 W/mm²
Leakage power: 5-15% of total at advanced nodes, depending on Vt mix
Activity factors: Typical 0.15-0.25 for logic, 0.05-0.15 for memories""",
                    "metadata": {"reference_design": "high_end_gpu"}
                }
            ],
            "area_models": [
                {
                    "id": "area_gpu_allocation",
                    "category": "area_models",
                    "source": "Die Shot Analysis (WikiChip, etc.)",
                    "content": """Typical High-End GPU Area Budget Allocation:
- SM array (compute cores): 35-45% of die area
  - Each SM: ~4-6 mm² on TSMC 4nm (varies by generation)
- L2 Cache: 15-25% of die area
  - SRAM density: ~0.2-0.3 Mbit/mm² at advanced nodes
- Memory controllers + PHY: 10-15% of die area
  - Each 32-bit memory controller slice: ~2-3 mm²
- NoC/Interconnect fabric: 8-12% of die area
- NVLink/PCIe PHYs: 8-12% of die area
  - Each high-speed SerDes lane: ~0.1-0.2 mm²
- Clock/Power/Test/Other: 5-10% of die area

Reticle limit: 858 mm² (33mm × 26mm maximum single die)
Chiplet strategy required beyond ~800 mm² for yield reasons
Typical GPU die sizes:
- Hopper H100: 814 mm² (near reticle limit)
- Ampere A100: 826 mm²
- Blackwell GB100: ~600 mm² per die × 2 dies (chiplet)""",
                    "metadata": {"reference_design": "high_end_gpu"}
                }
            ]
        }
