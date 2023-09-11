import numpy as np
import open3d as o3d

import random
from typing import Optional

from slam.octree.base_octree import Octree
from slam.octree.segmenters.base_plane_segmenter import PlaneSegmenter
from slam.typing.hints import Array3, ArrayNx3, ArrayNx8

__all__ = ["DepthOctree", "DepthOctreeNode"]


class DepthOctree(Octree):
    """
    Represents depth octree implementation, which uses depth parameter as final segmentation factor

    Parameters
    ----------
    depth: int
        Depth of octree
    """

    def __init__(
        self,
        depth: int = 1,
    ) -> None:
        self.__root: Optional[DepthOctreeNode] = None
        self.__depth: int = depth

    def build(self, point_cloud: o3d.geometry.PointCloud) -> None:
        """
        Represents implementation of abstract method to build octree

        Parameters
        ----------
        point_cloud: o3d.geometry.PointCloud
            Point cloud, which uses to build octree
        """
        if len(point_cloud.points) == 0:
            raise ValueError("Size of point cloud must be positive")

        self.__root = DepthOctreeNode(
            point_cloud.get_min_bound(), point_cloud.get_max_bound()
        )

        for point in point_cloud.points:
            self.__root.insert(point, self.__depth)

        self.__root.__points = None

    def segment(self, segmenter: PlaneSegmenter) -> None:
        """
        Represents implementation of abstract method to segment planes from built octree

        Parameters
        ----------
        segmenter: PlaneSegmenter
            Plane segmentation mechanism
        """
        if self.__root is None:
            raise AttributeError("There is nothing to segment. Please, build octree first.")

        self.__root.segment(segmenter, self.__depth)

    def visualize(self) -> None:
        """
        Represents abstract method to visualize segmented point cloud.
        """
        point_cloud = self.__root.get_colorized(self.__depth)
        o3d.visualization.draw(point_cloud)

    @property
    def depth(self) -> int:
        """
        Represents depth property of current implementation

        Returns
        -------
        depth: int
            Depth of octree
        """
        return self.__depth


class DepthOctreeNode:
    """
    Represents node of Depth Octree, which contains all necessary information

    Parameters
    ----------
    bottom_bound: Array3[np.float64]
        Bottom bound of current node
    top_bound: Array3[np.float64]
        Top bound of current node
    """

    def __init__(
        self, bottom_bound: Array3[np.float64], top_bound: Array3[np.float64]
    ) -> None:
        self.__top_bound: Array3[np.float64] = top_bound
        self.__bottom_bound: Array3[np.float64] = bottom_bound
        self.__children: Optional[ArrayNx8[DepthOctreeNode]] = [None] * 8
        self.__points: Optional[ArrayNx3[np.float64]] = None

    def insert(self, point: Array3[np.float64], depth: int) -> None:
        """
        Inserts point into the points list

        Parameters
        ----------
        point: Array3[np.float64]
            Point to insert
        depth: int
            Depth to insert a point
        """
        if depth == 0:
            if self.__points is None:
                self.__points = np.array([point])

            self.__points = np.append(self.__points, [point], axis=0)
            return

        node, octet = self._calculate_octet(point)
        if self.__children[octet] is None:
            self.__children[octet] = node

        self.__children[octet].insert(point, depth - 1)

    def segment(self, segmenter: PlaneSegmenter, depth: int) -> None:
        """
        Segments planes using segmenter in children nodes

        Parameters
        ----------
        segmenter: PlaneSegmenter
            Plane segmentation mechanism
        depth: int
            Depth to insert a point
        """
        if depth == 0:
            inliers = segmenter.segment(self.__points)
            self.__points = np.take(self.__points, inliers, axis=0)
            return

        for child in self.__children:
            if child is None:
                continue

            child.segment(segmenter, depth - 1)

    def get_colorized(self, depth: int) -> o3d.geometry.PointCloud:
        """
        Colorize segmented point cloud

        Parameters
        ----------
        depth: int
            Depth of current node

        Returns
        -------
        point_cloud: o3d.geometry.PointCloud
            Colorized segmented point cloud
        """
        if depth == 0:
            point_cloud = o3d.geometry.PointCloud(
                o3d.utility.Vector3dVector(self.__points)
            )
            point_cloud.paint_uniform_color(
                [random.random(), random.random(), random.random()]
            )
            return point_cloud

        point_cloud = o3d.geometry.PointCloud()
        for child in self.__children:
            if child is None:
                continue

            point_cloud += child.get_colorized(depth - 1)

        return point_cloud

    def _calculate_octet(self, point: Array3[np.float64]):
        """
        Calculate octet number using point

        Parameters
        ----------
        point: Array3[np.float64]
            Point to insert

        Returns
        -------
        node: DepthOctreeNode
            New children node
        octet: int
            Number of octet to which a point is inserted
        """
        center = (self.__top_bound + self.__bottom_bound) / 2
        diff = np.array([0, 0, 0])

        if point[0] < center[0]:
            if point[1] < center[1]:
                if point[2] < center[2]:
                    diff = np.array([0, 0, 0])
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 0
                else:
                    diff[2] += center[2]
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 4
            else:
                diff[1] += center[1]
                if point[2] < center[2]:
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 1
                else:
                    diff[2] += center[2]
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 5
        else:
            diff[0] += center[0]
            if point[1] < center[1]:
                if point[2] < center[2]:
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 3
                else:
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 7
            else:
                diff[1] += center[1]
                if point[2] < center[2]:
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 2
                else:
                    diff[2] += center[2]
                    return DepthOctreeNode(self.__bottom_bound + diff, center + diff), 6
