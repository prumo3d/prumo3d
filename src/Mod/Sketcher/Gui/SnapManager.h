/***************************************************************************
 *   Copyright (c) 2023 Pierre-Louis Boyer <pierrelouis.boyer@gmail.com>   *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 *   SnapManager initially funded by the Open Toolchain Foundation         *
 ***************************************************************************/

#ifndef SKETCHERGUI_SnapManager_H
#define SKETCHERGUI_SnapManager_H

#include <App/Application.h>

#include <vector>

#include <Base/Tools2D.h>
#include <Base/Vector3D.h>

namespace Part
{
class GeomCurve;
class GeomLineSegment;
class GeomArcOfCircle;
}  // namespace Part

namespace SketcherGui
{

class ViewProviderSketch;


class ViewProviderSketchSnapAttorney
{
private:
    static inline int getPreselectPoint(const ViewProviderSketch& vp);
    static inline int getPreselectCross(const ViewProviderSketch& vp);
    static inline int getPreselectCurve(const ViewProviderSketch& vp);
    // Prumo 3D: pontos-ímã (quadrantes, pontos médios e interseções)
    static inline bool isHandlerActive(const ViewProviderSketch& vp);
    static inline void drawSnapMarkers(
        ViewProviderSketch& vp,
        const std::vector<Base::Vector2d>& markers,
        int active
    );

    friend class SnapManager;
};

enum class SnapType
{
    None = 0x0,
    Angle = 0x1,
    Point = 0x2,
    Edge = 0x4,
    Grid = 0x8,

    All = Angle | Point | Edge | Grid
};

/// Prumo 3D: tipo de ponto-ímã encontrado perto do cursor
enum class KeyPointKind
{
    None,
    Quadrant,      ///< 0°, 90°, 180° e 270° de círculos e arcos
    Midpoint,      ///< ponto médio de linha
    AxisVertex,    ///< extremidades dos eixos de elipses
    Intersection,  ///< cruzamento entre duas curvas
};

/// Prumo 3D: último ponto-ímã usado pelo snap (lido pelas restrições automáticas)
struct KeyPointSnap
{
    bool valid = false;
    Base::Vector2d pos;
    KeyPointKind kind = KeyPointKind::None;
    int geoId1 = -2000;  // GeoEnum::GeoUndef
    int geoId2 = -2000;
};

/* This class is used to manage the overriding of mouse pointer coordinates in Sketcher
 *  (in Edit-Mode) depending on the situation. Those situations are in priority order :
 *  1 - Snap at angle: For tools like Slot, Arc, Line, Ellipse, this enables to constrain the angle
 * at steps of 5° (or customized angle). This is useful to make features at a certain angle (45° for
 * example) 2 - Snap to object: This snaps the mouse pointer onto objects. 3 - Snap to grid: This
 * snaps the mouse pointer on the grid.
 */
class SnapManager
{

    /** @brief      Class for monitoring changes in parameters affecting Snapping
     *  @details
     *
     * This nested class is a helper responsible for attaching to the parameters relevant for
     * SnapManager, initialising the SnapManager to the current configuration
     * and handle in real time any change to their values.
     */
    class ParameterObserver: public ParameterGrp::ObserverType
    {
    public:
        explicit ParameterObserver(SnapManager& client);
        ~ParameterObserver() override;

        void subscribeToParameters();

        void unsubscribeToParameters();

        /** Observer for parameter group. */
        void OnChange(Base::Subject<const char*>& rCaller, const char* sReason) override;

    private:
        void initParameters();
        void updateSnapParameter(const std::string& parametername);
        void updateSnapToObjectParameter(const std::string& parametername);
        void updateSnapToGridParameter(const std::string& parametername);
        void updateSnapAngleParameter(const std::string& parametername);
        void updateSnapToKeyPointsParameter(const std::string& parametername);

        static ParameterGrp::handle getParameterGrpHandle();

    private:
        std::map<std::string, std::function<void(const std::string&)>> str2updatefunction;
        SnapManager& client;
    };

public:
    explicit SnapManager(ViewProviderSketch& vp);
    ~SnapManager();

    Base::Vector2d snap(Base::Vector2d inputPos, SnapType mask);
    bool snapAtAngle(Base::Vector2d inputPos, Base::Vector2d& snapPos);
    bool snapToObject(Base::Vector2d inputPos, Base::Vector2d& snapPos, SnapType mask);
    bool snapToGrid(Base::Vector2d inputPos, Base::Vector2d& snapPos);

    bool snapToLineMiddle(Base::Vector3d& pointToOverride, const Part::GeomLineSegment* line);
    bool snapToArcMiddle(Base::Vector3d& pointToOverride, const Part::GeomArcOfCircle* arc);

    void setAngleSnapping(bool enable, Base::Vector2d referencepoint);

    /// Prumo 3D: ponto-ímã usado no último snap (valid = false se o último snap não foi num ímã)
    const KeyPointSnap& getLastKeyPointSnap() const
    {
        return lastKeyPointSnap;
    }
    /// Prumo 3D: apaga os marcadores de pontos-ímã da tela
    void clearKeyPointMarkers();

    struct SnapHandle
    {
        SnapManager* mgr = nullptr;
        Base::Vector2d cursorPos;

        SnapHandle(SnapManager* m, const Base::Vector2d& cursorPos)
            : mgr(m)
            , cursorPos(cursorPos)
        {}

        Base::Vector2d compute(SnapType mask = SnapType::All);
    };

private:
    /// Reference to ViewProviderSketch in order to access the public and the Attorney Interface
    ViewProviderSketch& viewProvider;

    bool angleSnapRequested;
    bool snapRequested;
    bool snapToObjectsRequested;
    bool snapToGridRequested;
    bool snapToKeyPointsRequested;

    /// Prumo 3D: procura pontos-ímã perto do cursor, desenha os marcadores e devolve o mais
    /// próximo dentro da tolerância de captura
    bool findKeyPoint(Base::Vector2d inputPos, bool showMarkers, KeyPointSnap& found);

    KeyPointSnap lastKeyPointSnap;
    bool keyPointMarkersShown = false;

    Base::Vector2d referencePoint;
    double lastMouseAngle;

    double snapAngle;

    /// Observer to track all the needed parameters.
    std::unique_ptr<SnapManager::ParameterObserver> pObserver;
};


}  // namespace SketcherGui


#endif  // SKETCHERGUI_SnapManager_H
