#!/usr/bin/env python3

import os
import sys
import json

import kipy
import kipy.board
import kipy.board_types

class ItemNode:
    def __init__(self, item: kipy.board_types.Pad | kipy.board_types.Track | kipy.board_types.Via):
        self.item = item
        self.connected_items = []

    def add_connected_item(self, item: "ItemNode"):
        self.connected_items.append(item)

    def __str__(self):
        return f"{self.item} -> {self.connected_items}"
    
    def __repr__(self):
        return f"{type(self.item)}: {self.item} -> {self.connected_items}"
    
    def __eq__(self, other):
        return self.item.id == other.item.id
    
    def __hash__(self):
        return hash(self.item)

class FlyDB:

    def __init__(self, board: kipy.board.Board):
        self.board: kipy.board.Board = board
        self.refresh_items()
        self.build_item_graph()

    def refresh_items(self):
        self.tracks = self.board.get_tracks()
        self.vias = self.board.get_vias()
        self.pads = self.board.get_pads()

    def build_item_graph(self):
        self.item_nodes: list[ItemNode] = []

        for pad in self.pads:
            node = ItemNode(pad)
            self.item_nodes.append(node)

        for track in self.tracks:
            node = ItemNode(track)
            self.item_nodes.append(node)

        for via in self.vias:
            node = ItemNode(via)
            self.item_nodes.append(node)

        for node in self.item_nodes:
            connected_items = self._get_connected_items(node.item)
            for item in connected_items:
                connected_node = self.get_node_by_item(item)
                node.add_connected_item(connected_node)

    def get_node_by_item(self, item: kipy.board_types.Pad | kipy.board_types.Track | kipy.board_types.Via) -> ItemNode:
        for node in self.item_nodes:
            if node.item.id == item.id:
                return node
        raise ValueError(f"Item {item} not found")
    
    def _get_connected_items(self, item: kipy.board_types.Pad | kipy.board_types.Track | kipy.board_types.Via) -> list:
        items = []

        if (type(item) == kipy.board_types.Pad):
            item_layers = item.padstack.layers
        elif (type(item) == kipy.board_types.Track):
            item_layers = [item.layer]
        elif (type(item) == kipy.board_types.Via):
            item_layers = item.padstack.layers
        else:
            raise ValueError(f"Item type {type(item)} not supported")

        for track in self.tracks:
            if (track.layer not in item_layers):
                continue
            if self.board.hit_test(item, track.start) or self.board.hit_test(item, track.end):
                if item.id != track.id:
                    items.append(track)
        for via in self.vias:
            if not all(layer in via.padstack.layers for layer in item_layers):
                continue
            if self.board.hit_test(item, via.position):
                if item.id != via.id:
                    items.append(via)
        for pad in self.pads:
            if not all(layer in pad.padstack.layers for layer in item_layers):
                continue
            if self.board.hit_test(item, pad.position):
                if item.id != pad.id:
                    items.append(pad)
        return items
    
    def get_path_bfs(self, start: ItemNode, end: ItemNode) -> list[kipy.board_types.Track | kipy.board_types.Via | kipy.board_types.Pad]:
        visited = set()
        queue = [[start]]
        if start == end:
            return [start.item]
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node not in visited:
                connected_nodes = node.connected_items
                for connected_node in connected_nodes:
                    new_path = list(path)
                    new_path.append(connected_node)
                    queue.append(new_path)
                    if connected_node == end:
                        return [node.item for node in new_path]
                visited.add(node)
        return []
    
    def get_between(self, pad1: kipy.board_types.Pad, pad2: kipy.board_types.Pad) -> list[kipy.board_types.Track | kipy.board_types.Via | kipy.board_types.Pad]:
        node1 = self.get_node_by_item(pad1)
        node2 = self.get_node_by_item(pad2)

        return self.get_path_bfs(node1, node2)

class FlyTools:

    def __init__(self, board: kipy.board.Board, flytime_info):
        self.board: kipy.board.Board = board
        self.flytime_info = flytime_info
        self.flydb = FlyDB(board)

    def _get_footprint_by_ref(self, ref: str) -> kipy.board_types.Footprint:
        footprints = self.board.get_footprints()
        for footprint in footprints:
            if footprint.reference_field.text.value == ref:
                return footprint
        raise ValueError(f"Footprint {ref} not found")
            
    def _get_pad_from_fp(self, fp: kipy.board_types.FootprintInstance, padnum: str) -> kipy.board_types.Pad:
        for pad in fp.definition.pads:
            if pad.number == padnum:
                return pad
        raise ValueError(f"Pad {padnum} not found in footprint {fp.reference_field.text.value}")

    def get_objs_bewteen_pads(self, pad1: str, pad2: str) -> list[kipy.board_types.Track | kipy.board_types.Via | kipy.board_types.Pad]:
        des1 = pad1.strip().split(".")[0]
        des2 = pad2.strip().split(".")[0]
        
        fp1 = self._get_footprint_by_ref(des1)
        fp2 = self._get_footprint_by_ref(des2)

        pad1 = pad1.strip().split(".")[1]
        pad2 = pad2.strip().split(".")[1]

        pad1 = self._get_pad_from_fp(fp1, pad1)
        pad2 = self._get_pad_from_fp(fp2, pad2)

        return self.flydb.get_between(pad1, pad2)

if __name__ == "__main__":

    # if len(sys.argv) < 2:
    #     print("Usage: flytools.py <spreadsheet>")
    #     sys.exit(1)

    # xlsxfile = sys.argv[2]
    xlsxfile = "flytimes_example.xlsx"

    kicad = kipy.KiCad()
    board = kicad.get_board()

    flytools = FlyTools(board, "flytime_info.json")

    objs = flytools.get_objs_bewteen_pads("TP101.1", "TP102.1")

    board.add_to_selection(objs)
