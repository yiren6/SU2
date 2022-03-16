/*!
 * \file CQuadrilateral.cpp
 * \brief Main classes for defining the primal grid elements
 * \author F. Palacios
 * \version 7.3.0 "Blackbird"
 *
 * SU2 Project Website: https://su2code.github.io
 *
 * The SU2 Project is maintained by the SU2 Foundation
 * (http://su2foundation.org)
 *
 * Copyright 2012-2022, SU2 Contributors (cf. AUTHORS.md)
 *
 * SU2 is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * SU2 is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with SU2. If not, see <http://www.gnu.org/licenses/>.
 */

#include "../../../include/geometry/primal_grid/CQuadrilateral.hpp"
#include "../../../include/option_structure.hpp"

constexpr unsigned short CQuadrilateralConnectivity::nNodesFace[4];
constexpr unsigned short CQuadrilateralConnectivity::Faces[4][2];
constexpr unsigned short CQuadrilateralConnectivity::nNeighbor_Nodes[4];
constexpr unsigned short CQuadrilateralConnectivity::Neighbor_Nodes[4][2];

CQuadrilateral::CQuadrilateral(unsigned long val_point_0, unsigned long val_point_1,
             unsigned long val_point_2, unsigned long val_point_3, unsigned short val_nDim):
  CPrimalGridWithConnectivity<CQuadrilateralConnectivity>(false)
{
  /*--- Define face structure of the element ---*/
  Nodes[0] = val_point_0;
  Nodes[1] = val_point_1;
  Nodes[2] = val_point_2;
  Nodes[3] = val_point_3;

  unsigned short nFaces = 4;  

  unsigned short iDim, iFace, iNeighbor_Elements;

  /*--- Allocate CG coordinates ---*/
  nDim = val_nDim;

  Coord_FaceElems_CG = new su2double* [nFaces];
  for (iFace = 0; iFace < nFaces; iFace++) {
    Coord_FaceElems_CG[iFace] = new su2double [nDim];
    for (iDim = 0; iDim < nDim; iDim++)
      Coord_FaceElems_CG[iFace][iDim] = 0.0;
  }
}

void CQuadrilateral::Change_Orientation() {
  std::swap(Nodes[1], Nodes[3]);
}

CQuadrilateral::~CQuadrilateral() {
  unsigned short iFaces;
  unsigned short nFaces = 4;

  for (iFaces = 0; iFaces < nFaces; iFaces++)
    if (Coord_FaceElems_CG[iFaces] != nullptr) delete[] Coord_FaceElems_CG[iFaces];
  delete[] Coord_FaceElems_CG;

}
