/*!
 * \file CNSSolver.hpp
 * \brief Headers of the CNSSolver class
 * \author F. Palacios, T. Economon
 * \version 7.0.5 "Blackbird"
 *
 * SU2 Project Website: https://su2code.github.io
 *
 * The SU2 Project is maintained by the SU2 Foundation
 * (http://su2foundation.org)
 *
 * Copyright 2012-2020, SU2 Contributors (cf. AUTHORS.md)
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

#pragma once

#include "CEulerSolver.hpp"

/*!
 * \class CNSSolver
 * \brief Main class for defining the Navier-Stokes flow solver.
 * \ingroup Navier_Stokes_Equations
 * \author F. Palacios
 */
class CNSSolver final : public CEulerSolver {
private:
  su2double
  *Surface_Buffet_Metric = nullptr, /*!< \brief Integrated separation sensor for each monitoring surface. */
  *Buffet_Metric = nullptr,         /*!< \brief Integrated separation sensor for each boundary. */
  ***HeatConjugateVar = nullptr,    /*!< \brief Conjugate heat transfer variables for each boundary and vertex. */
  **Buffet_Sensor = nullptr,        /*!< \brief Separation sensor for each boundary and vertex. */
  Total_Buffet_Metric;              /*!< \brief Integrated separation sensor for all the boundaries. */

  /*!
   * \brief A virtual member.
   * \param[in] geometry - Geometrical definition.
   * \param[in] config - Definition of the particular problem.
   */
  void SetRoe_Dissipation(CGeometry *geometry, CConfig *config) override;

  /*!
   * \brief Compute the velocity^2, SoundSpeed, Pressure, Enthalpy, Viscosity.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] config - Definition of the particular problem.
   * \param[in] Output - boolean to determine whether to print output.
   * \return - The number of non-physical points.
   */
  unsigned long SetPrimitive_Variables(CSolver **solver_container,
                                       CConfig *config, bool Output) override;

  /*!
   * \brief Common code for wall boundaries, add the residual and Jacobian
   * contributions due to grid motion associated with a particular boundary point.
   */
  void AddDynamicGridResidualContribution(unsigned long iPoint,
                                          unsigned long Point_Normal,
                                          CGeometry* geometry,
                                          const su2double* UnitNormal,
                                          su2double Area,
                                          const su2double* GridVel,
                                          su2double** Jacobian_i,
                                          su2double& Res_Conv,
                                          su2double& Res_Visc) const;

  /*!
   * \brief Get the wall temperature at a given vertex of a given marker for CHT problems.
   */
  su2double GetCHTWallTemperature(const CConfig* config,
                                  unsigned short val_marker,
                                  unsigned long iVertex,
                                  su2double thermal_conductivity,
                                  su2double dist_ij,
                                  su2double There,
                                  su2double Temperature_Ref) const;

  /*!
   * \brief Generic implementation of the isothermal wall also covering CHT cases,
   * for which the wall temperature is given by GetCHTWallTemperature.
   */
  void BC_Isothermal_Wall_Generic(CGeometry *geometry,
                                  CSolver **solver_container,
                                  CNumerics *conv_numerics,
                                  CNumerics *visc_numerics,
                                  CConfig *config,
                                  unsigned short val_marker,
                                  bool cht_mode = false);

public:
  /*!
   * \brief Constructor of the class.
   */
  CNSSolver(void);

  /*!
   * \overload
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] config - Definition of the particular problem.
   */
  CNSSolver(CGeometry *geometry, CConfig *config, unsigned short iMesh);

  /*!
   * \brief Destructor of the class.
   */
  ~CNSSolver(void) override;

  /*!
   * \brief Provide the buffet metric.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \return Value of the buffet metric on the surface <i>val_marker</i>.
   */
  inline su2double GetSurface_Buffet_Metric(unsigned short val_marker) const override { return Surface_Buffet_Metric[val_marker]; }

  /*!
   * \brief Get the buffet metric.
   * \return Value of the buffet metric.
   */
  inline su2double GetTotal_Buffet_Metric() const override { return Total_Buffet_Metric; }

  /*!
   * \brief Restart residual and compute gradients.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] config - Definition of the particular problem.
   * \param[in] iRKStep - Current step of the Runge-Kutta iteration.
   * \param[in] RunTime_EqSystem - System of equations which is going to be solved.
   * \param[in] Output - boolean to determine whether to print output.
   */
  void Preprocessing(CGeometry *geometry,
                    CSolver **solver_container,
                    CConfig *config,
                    unsigned short iMesh,
                    unsigned short iRKStep,
                    unsigned short RunTime_EqSystem,
                    bool Output) override;

  /*!
   * \brief Compute weighted-sum "combo" objective output
   * \param[in] config - Definition of the particular problem.
   */
  void Evaluate_ObjFunc(CConfig *config) override;

  /*!
   * \brief Impose a constant heat-flux condition at the wall.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] conv_numerics - Description of the numerical method.
   * \param[in] visc_numerics - Description of the numerical method.
   * \param[in] config - Definition of the particular problem.
   * \param[in] val_marker - Surface marker where the boundary condition is applied.
   */
  void BC_HeatFlux_Wall(CGeometry *geometry,
                        CSolver **solver_container,
                        CNumerics *conv_numerics,
                        CNumerics *visc_numerics,
                        CConfig *config,
                        unsigned short val_marker) override;

  /*!
   * \brief Impose the Navier-Stokes boundary condition (strong).
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] conv_numerics - Description of the numerical method.
   * \param[in] visc_numerics - Description of the numerical method.
   * \param[in] config - Definition of the particular problem.
   * \param[in] val_marker - Surface marker where the boundary condition is applied.
   */
  void BC_Isothermal_Wall(CGeometry *geometry,
                          CSolver **solver_container,
                          CNumerics *conv_numerics,
                          CNumerics *visc_numerics,
                          CConfig *config,
                          unsigned short val_marker) override;

  /*!
   * \brief Impose the Navier-Stokes boundary condition (strong) with values from a CHT coupling.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] conv_numerics - Description of the numerical method.
   * \param[in] visc_numerics - Description of the numerical method.
   * \param[in] config - Definition of the particular problem.
   * \param[in] val_marker - Surface marker where the boundary condition is applied.
   */
  void BC_ConjugateHeat_Interface(CGeometry *geometry,
                                  CSolver **solver_container,
                                  CNumerics *numerics,
                                  CConfig *config,
                                  unsigned short val_marker) override;

  /*!
   * \brief Set the conjugate heat variables.
   * \param[in] val_marker        - marker index
   * \param[in] val_vertex        - vertex index
   * \param[in] pos_var           - variable position (in vector of all conjugate heat variables)
   */
  inline su2double GetConjugateHeatVariable(unsigned short val_marker,
                                            unsigned long val_vertex,
                                            unsigned short pos_var) const override {
    return HeatConjugateVar[val_marker][val_vertex][pos_var];
  }

  /*!
   * \brief Set the conjugate heat variables.
   * \param[in] val_marker        - marker index
   * \param[in] val_vertex        - vertex index
   * \param[in] pos_var           - variable position (in vector of all conjugate heat variables)
   * \param[in] relaxation factor - relaxation factor for the change of the variables
   * \param[in] val_var           - value of the variable
   */
  inline void SetConjugateHeatVariable(unsigned short val_marker,
                                       unsigned long val_vertex,
                                       unsigned short pos_var,
                                       su2double relaxation_factor,
                                       su2double val_var) override {
    HeatConjugateVar[val_marker][val_vertex][pos_var] = relaxation_factor*val_var + (1.0-relaxation_factor)*HeatConjugateVar[val_marker][val_vertex][pos_var];
  }

  /*!
   * \brief Compute the buffet sensor.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] config - Definition of the particular problem.
   */
  void Buffet_Monitoring(CGeometry *geometry, CConfig *config) override;

  /*!
   * \brief Compute the viscous contribution for a particular edge.
   * \param[in] iEdge - Edge for which the flux and Jacobians are to be computed.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] numerics - Description of the numerical method.
   * \param[in] config - Definition of the particular problem.
   */
  void Viscous_Residual(unsigned long iEdge, CGeometry *geometry, CSolver **solver_container,
                        CNumerics *numerics, CConfig *config) override;

  /*!
   * \brief Get the skin friction coefficient.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the skin friction coefficient.
   */
    inline su2double GetCSkinFriction(unsigned short val_marker,
                                    unsigned long val_vertex,
                                    unsigned short val_dim) const override {
    return CSkinFriction[val_marker][val_dim][val_vertex];
  }

  /*!
   * \brief Get the skin friction coefficient.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the heat transfer coefficient.
   */
  inline su2double GetHeatFlux(unsigned short val_marker, unsigned long val_vertex) const override {
    return HeatFlux[val_marker][val_vertex];
  }

  /*!
   * \brief Get the skin friction coefficient.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the heat transfer coefficient.
   */
  inline su2double GetHeatFluxTarget(unsigned short val_marker, unsigned long val_vertex) const override {
    return HeatFluxTarget[val_marker][val_vertex];
  }

  /*!
   * \brief Set the value of the target Pressure coefficient.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the pressure coefficient.
   */
  inline void SetHeatFluxTarget(unsigned short val_marker,
                                unsigned long val_vertex,
                                su2double val_heat) override { HeatFluxTarget[val_marker][val_vertex] = val_heat; }

  /*!
   * \brief Get the value of the buffet sensor
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the buffet sensor.
   */
  inline su2double GetBuffetSensor(unsigned short val_marker, unsigned long val_vertex) const override {
    return Buffet_Sensor[val_marker][val_vertex];
  }

  /*!
   * \brief Get the y plus.
   * \param[in] val_marker - Surface marker where the coefficient is computed.
   * \param[in] val_vertex - Vertex of the marker <i>val_marker</i> where the coefficient is evaluated.
   * \return Value of the y plus.
   */
  inline su2double GetYPlus(unsigned short val_marker, unsigned long val_vertex) const override {
    return YPlus[val_marker][val_vertex];
  }

  /*!
   * \brief Computes the wall shear stress (Tau_Wall) on the surface using a wall function.
   * \param[in] geometry - Geometrical definition of the problem.
   * \param[in] solver_container - Container vector with all the solutions.
   * \param[in] config - Definition of the particular problem.
   */
  void SetTauWall_WF(CGeometry *geometry,
                     CSolver** solver_container,
                     CConfig* config) override;

};
