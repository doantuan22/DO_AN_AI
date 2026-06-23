# Kho dữ liệu metadata, ảnh và graph dành riêng cho bản đồ con

from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SubMap:
    id: str
    main_node_id: str
    name: str
    floor: int
    image: str
    graph_file: str
    rotation: float = 0.0
    entry_position: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("main_node_id", None)
        data["entry_position"] = self.entry_position or {"x": 0.0, "y": 0.0}
        return data


class SubMapStore:
    # Quản lý index và tài nguyên của các bản đồ con trong project

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()
        self.assets_dir = self.base_dir / "assets" / "sub_maps"
        self.graphs_dir = self.base_dir / "data" / "sub_maps"
        self.index_path = self.base_dir / "data" / "sub_map_index.json"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index({"version": 1, "nodes": {}})

    @staticmethod
    def slugify(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.strip())
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
        slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
        return slug or "sub_map"

    def list_for_node(self, main_node_id: str) -> List[SubMap]:
        raw = self._read_index().get("nodes", {}).get(main_node_id, [])
        maps = [self._from_dict(main_node_id, item) for item in raw]
        return sorted(maps, key=lambda item: (item.floor, item.name.lower()))

    def has_sub_maps(self, main_node_id: str) -> bool:
        return bool(self.list_for_node(main_node_id))

    def get(self, sub_map_id: str) -> SubMap:
        for node_id, items in self._read_index().get("nodes", {}).items():
            for item in items:
                if item.get("id") == sub_map_id:
                    return self._from_dict(node_id, item)
        raise KeyError(f"Không tìm thấy bản đồ con '{sub_map_id}'")

    def create(
        self,
        main_node_id: str,
        name: str,
        floor: int,
        source_image: str,
    ) -> SubMap:
        main_node_id = main_node_id.strip()
        name = name.strip()
        if not main_node_id or not name:
            raise ValueError("Node chính và tên bản đồ con không được để trống")
        source = Path(source_image)
        if not source.is_file():
            raise FileNotFoundError("Ảnh bản đồ con không tồn tại")
        self._validate_unique_name(main_node_id, int(floor), name)

        base_slug = self.slugify(f"{name}_tang_{floor}")
        sub_map_id = self._unique_id(base_slug)
        image_target = self._unique_path(self.assets_dir, base_slug, source.suffix.lower() or ".png")
        graph_target = self._unique_path(self.graphs_dir, base_slug, ".json")
        shutil.copy2(source, image_target)

        graph_data = {
            "map_id": sub_map_id,
            "name": name,
            "floor": int(floor),
            "coordinate_system": "pixel coordinates, origin at top-left",
            "nodes": [],
            "edges": [],
        }
        self.write_graph_path(graph_target, graph_data)
        item = SubMap(
            id=sub_map_id,
            main_node_id=main_node_id,
            name=name,
            floor=int(floor),
            image=self.relative_path(image_target),
            graph_file=self.relative_path(graph_target),
            entry_position={"x": 0.0, "y": 0.0},
        )
        index = self._read_index()
        index.setdefault("nodes", {}).setdefault(main_node_id, []).append(item.to_dict())
        self._write_index(index)
        return item

    def update(self, sub_map_id: str, **changes: Any) -> SubMap:
        current = self.get(sub_map_id)
        new_node_id = str(changes.get("main_node_id", current.main_node_id)).strip()
        new_name = str(changes.get("name", current.name)).strip()
        new_floor = int(changes.get("floor", current.floor))
        if not new_node_id or not new_name:
            raise ValueError("Node chính và tên bản đồ con không được để trống")
        self._validate_unique_name(new_node_id, new_floor, new_name, excluding_id=sub_map_id)

        image = current.image
        source_image = changes.get("source_image")
        if source_image:
            source = Path(str(source_image))
            if not source.is_file():
                raise FileNotFoundError("Ảnh bản đồ con không tồn tại")
            target = self._unique_path(
                self.assets_dir, self.slugify(f"{new_node_id}_{new_name}_tang_{new_floor}"),
                source.suffix.lower() or ".png",
            )
            shutil.copy2(source, target)
            image = self.relative_path(target)

        graph_file = current.graph_file
        if changes.get("rename_graph_file"):
            current_graph_path = self.absolute_path(current.graph_file)
            target_stem = self.slugify(f"{new_name}_tang_{new_floor}")
            if current_graph_path.stem != target_stem and self._is_managed_path(current_graph_path):
                target_graph_path = self._unique_path(
                    self.graphs_dir,
                    target_stem,
                    current_graph_path.suffix or ".json",
                )
                if current_graph_path.exists():
                    os.replace(current_graph_path, target_graph_path)
                graph_file = self.relative_path(target_graph_path)

        entry = changes.get("entry_position", current.entry_position) or {"x": 0.0, "y": 0.0}
        updated = SubMap(
            id=current.id,
            main_node_id=new_node_id,
            name=new_name,
            floor=new_floor,
            image=image,
            graph_file=graph_file,
            rotation=float(changes.get("rotation", current.rotation)) % 360,
            entry_position={"x": float(entry.get("x", 0)), "y": float(entry.get("y", 0))},
        )
        index = self._read_index()
        for node_id, items in list(index.get("nodes", {}).items()):
            index["nodes"][node_id] = [item for item in items if item.get("id") != sub_map_id]
            if not index["nodes"][node_id]:
                index["nodes"].pop(node_id)
        index.setdefault("nodes", {}).setdefault(new_node_id, []).append(updated.to_dict())
        self._write_index(index)

        graph = self.load_graph(updated)
        graph["map_id"] = updated.id
        graph["name"] = updated.name
        graph["floor"] = updated.floor
        self.save_graph(updated, graph)
        return updated

    def copy_to_node(
        self,
        source_sub_map_id: str,
        target_node_id: str,
        name: Optional[str] = None,
        floor: Optional[int] = None,
    ) -> SubMap:
        source = self.get(source_sub_map_id)
        target_node_id = target_node_id.strip()
        new_name = (name or source.name).strip()
        new_floor = int(source.floor if floor is None else floor)
        if not target_node_id or not new_name:
            raise ValueError("Node đích và tên bản đồ con không được để trống")
        if target_node_id == source.main_node_id:
            raise ValueError("Node đích phải khác node nguồn")
        self._validate_unique_name(target_node_id, new_floor, new_name)

        base_slug = self.slugify(f"{new_name}_tang_{new_floor}")
        sub_map_id = self._unique_id(base_slug)
        image = source.image
        source_image_path = self.absolute_path(source.image)
        if source_image_path.exists():
            image_target = self._unique_path(
                self.assets_dir,
                base_slug,
                source_image_path.suffix.lower() or ".png",
            )
            shutil.copy2(source_image_path, image_target)
            image = self.relative_path(image_target)
        graph_target = self._unique_path(self.graphs_dir, base_slug, ".json")

        graph_data = json.loads(json.dumps(self.load_graph(source), ensure_ascii=False))
        graph_data.update({
            "map_id": sub_map_id,
            "name": new_name,
            "floor": new_floor,
        })
        self.write_graph_path(graph_target, graph_data)

        item = SubMap(
            id=sub_map_id,
            main_node_id=target_node_id,
            name=new_name,
            floor=new_floor,
            image=image,
            graph_file=self.relative_path(graph_target),
            rotation=source.rotation,
            entry_position=dict(source.entry_position or {"x": 0.0, "y": 0.0}),
        )
        index = self._read_index()
        index.setdefault("nodes", {}).setdefault(target_node_id, []).append(item.to_dict())
        self._write_index(index)
        return item

    def delete(self, sub_map_id: str, delete_files: bool = False) -> None:
        current = self.get(sub_map_id)
        index = self._read_index()
        for node_id, items in list(index.get("nodes", {}).items()):
            index["nodes"][node_id] = [item for item in items if item.get("id") != sub_map_id]
            if not index["nodes"][node_id]:
                index["nodes"].pop(node_id)
        self._write_index(index)
        if delete_files:
            for value in (current.image, current.graph_file):
                path = self.absolute_path(value)
                if self._is_managed_path(path) and path.exists():
                    path.unlink()

    def load_graph(self, sub_map: SubMap | str) -> Dict[str, Any]:
        item = self.get(sub_map) if isinstance(sub_map, str) else sub_map
        path = self.absolute_path(item.graph_file)
        if not path.exists():
            return {"map_id": item.id, "name": item.name, "floor": item.floor, "nodes": [], "edges": []}
        try:
            with path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except json.JSONDecodeError as exc:
            raise ValueError(f"File graph bản đồ con không hợp lệ: {exc}") from exc
        data.setdefault("nodes", [])
        data.setdefault("edges", [])
        return data

    def save_graph(self, sub_map: SubMap | str, data: Dict[str, Any]) -> None:
        item = self.get(sub_map) if isinstance(sub_map, str) else sub_map
        data.update({"map_id": item.id, "name": item.name, "floor": item.floor})
        self.write_graph_path(self.absolute_path(item.graph_file), data)

    def absolute_path(self, relative: str) -> Path:
        return (self.base_dir / Path(relative.replace("/", os.sep))).resolve()

    def relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.base_dir).as_posix()

    def _validate_unique_name(
        self,
        node_id: str,
        floor: int,
        name: str,
        excluding_id: Optional[str] = None,
    ) -> None:
        normalized_name = name.strip().casefold()
        for item in self.list_for_node(node_id):
            if item.id == excluding_id:
                continue
            if item.floor != floor:
                continue
            if item.name.strip().casefold() == normalized_name:
                raise ValueError(
                    f"Node {node_id} đã có bản đồ con tên '{name}' ở tầng {floor}"
                )

    def _unique_id(self, base: str) -> str:
        existing = {item.id for node in self._read_index().get("nodes", {}) for item in self.list_for_node(node)}
        candidate, number = base, 2
        while candidate in existing:
            candidate, number = f"{base}_{number}", number + 1
        return candidate

    @staticmethod
    def _unique_path(directory: Path, stem: str, suffix: str) -> Path:
        candidate, number = directory / f"{stem}{suffix}", 2
        while candidate.exists():
            candidate, number = directory / f"{stem}_{number}{suffix}", number + 1
        return candidate

    def _is_managed_path(self, path: Path) -> bool:
        return self.assets_dir in path.parents or self.graphs_dir in path.parents

    def _read_index(self) -> Dict[str, Any]:
        try:
            with self.index_path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Không thể đọc sub_map_index.json: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("nodes", {}), dict):
            raise ValueError("sub_map_index.json không đúng cấu trúc")
        data.setdefault("version", 1)
        data.setdefault("nodes", {})
        return data

    def _write_index(self, data: Dict[str, Any]) -> None:
        temp = self.index_path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, self.index_path)

    @staticmethod
    def write_graph_path(path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)

    @staticmethod
    def _from_dict(node_id: str, data: Dict[str, Any]) -> SubMap:
        entry = data.get("entry_position") or {"x": 0, "y": 0}
        return SubMap(
            id=str(data["id"]), main_node_id=node_id, name=str(data.get("name", data["id"])),
            floor=int(data.get("floor", 1)), image=str(data.get("image", "")),
            graph_file=str(data.get("graph_file", "")), rotation=float(data.get("rotation", 0)),
            entry_position={"x": float(entry.get("x", 0)), "y": float(entry.get("y", 0))},
        )
