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
 ***************************************************************************/

#include <QApplication>

#include <algorithm>
#include <cmath>
#include <limits>

#include <Precision.hxx>
#include <Standard_Failure.hxx>

#include <Base/Tools.h>
#include <Mod/Part/App/Geometry.h>
#include <Mod/Sketcher/App/SketchObject.h>

#include "SnapManager.h"
#include "ViewProviderSketch.h"


using namespace SketcherGui;
using namespace Sketcher;

/************************************ Attorney *******************************************/

inline int ViewProviderSketchSnapAttorney::getPreselectPoint(const ViewProviderSketch& vp)
{
    return vp.getPreselectPoint();
}

inline int ViewProviderSketchSnapAttorney::getPreselectCross(const ViewProviderSketch& vp)
{
    return vp.getPreselectCross();
}

inline int ViewProviderSketchSnapAttorney::getPreselectCurve(const ViewProviderSketch& vp)
{
    return vp.getPreselectCurve();
}

inline bool ViewProviderSketchSnapAttorney::isHandlerActive(const ViewProviderSketch& vp)
{
    return vp.getSketchMode() == ViewProviderSketch::STATUS_SKETCH_UseHandler;
}

inline void ViewProviderSketchSnapAttorney::drawSnapAlignment(
    ViewProviderSketch& vp,
    const std::vector<Base::Vector2d>& segments
)
{
    vp.drawSnapAlignment(segments);
}

inline void ViewProviderSketchSnapAttorney::drawSnapMarkers(
    ViewProviderSketch& vp,
    const std::vector<Base::Vector2d>& markers,
    int active
)
{
    vp.drawSnapMarkers(markers, active);
}

/**************************** ParameterObserver nested class *****************************/
SnapManager::ParameterObserver::ParameterObserver(SnapManager& client)
    : client(client)
{
    initParameters();
    subscribeToParameters();
}

SnapManager::ParameterObserver::~ParameterObserver()
{
    unsubscribeToParameters();
}

void SnapManager::ParameterObserver::initParameters()
{
    // static map to avoid substantial if/else branching
    //
    // key->first               => String of parameter,
    // key->second              => Update function to be called for the parameter,
    str2updatefunction = {
        {"Snap", [this](const std::string& param) { updateSnapParameter(param); }},
        {"SnapToObjects", [this](const std::string& param) { updateSnapToObjectParameter(param); }},
        {"SnapToGrid", [this](const std::string& param) { updateSnapToGridParameter(param); }},
        {"SnapAngle", [this](const std::string& param) { updateSnapAngleParameter(param); }},
        {"SnapToKeyPoints",
         [this](const std::string& param) { updateSnapToKeyPointsParameter(param); }},
        {"SnapAlignment", [this](const std::string& param) { updateSnapAlignmentParameter(param); }},
    };

    for (auto& val : str2updatefunction) {
        auto string = val.first;
        auto function = val.second;

        function(string);
    }
}

void SnapManager::ParameterObserver::updateSnapParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapRequested = hGrp->GetBool(parametername.c_str(), true);
}

void SnapManager::ParameterObserver::updateSnapToObjectParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapToObjectsRequested = hGrp->GetBool(parametername.c_str(), true);
}

void SnapManager::ParameterObserver::updateSnapToGridParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapToGridRequested = hGrp->GetBool(parametername.c_str(), false);
}

void SnapManager::ParameterObserver::updateSnapAngleParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapAngle
        = fmod(Base::toRadians(hGrp->GetFloat(parametername.c_str(), 5.)), 2 * std::numbers::pi);
}

void SnapManager::ParameterObserver::updateSnapToKeyPointsParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapToKeyPointsRequested = hGrp->GetBool(parametername.c_str(), true);
    if (!client.snapToKeyPointsRequested) {
        client.clearKeyPointMarkers();
    }
}

void SnapManager::ParameterObserver::updateSnapAlignmentParameter(const std::string& parametername)
{
    ParameterGrp::handle hGrp = getParameterGrpHandle();

    client.snapToAlignmentRequested = hGrp->GetBool(parametername.c_str(), true);
    if (!client.snapToAlignmentRequested) {
        client.clearAlignmentLines();
    }
}

void SnapManager::ParameterObserver::subscribeToParameters()
{
    try {
        ParameterGrp::handle hGrp = getParameterGrpHandle();
        hGrp->Attach(this);
    }
    catch (const Base::ValueError& e) {  // ensure that if parameter strings are not well-formed,
                                         // the exception is not propagated
        Base::Console().developerError("SnapManager", "Malformed parameter string: %s\n", e.what());
    }
}

void SnapManager::ParameterObserver::unsubscribeToParameters()
{
    try {
        ParameterGrp::handle hGrp = getParameterGrpHandle();
        hGrp->Detach(this);
    }
    catch (const Base::ValueError& e) {  // ensure that if parameter strings are not well-formed,
                                         // the program is not terminated when calling the noexcept
                                         // destructor.
        Base::Console().developerError("SnapManager", "Malformed parameter string: %s\n", e.what());
    }
}

void SnapManager::ParameterObserver::OnChange(Base::Subject<const char*>& rCaller, const char* sReason)
{
    (void)rCaller;

    auto key = str2updatefunction.find(sReason);
    if (key != str2updatefunction.end()) {
        auto string = key->first;
        auto function = key->second;

        function(string);
    }
}

ParameterGrp::handle SnapManager::ParameterObserver::getParameterGrpHandle()
{
    return App::GetApplication().GetParameterGroupByPath(
        "User parameter:BaseApp/Preferences/Mod/Sketcher/Snap"
    );
}

//**************************** SnapManager class ******************************

SnapManager::SnapManager(ViewProviderSketch& vp)
    : viewProvider(vp)
    , angleSnapRequested(false)
    , snapRequested(true)
    , snapToObjectsRequested(true)
    , snapToGridRequested(false)
    , snapToKeyPointsRequested(true)
    , snapToAlignmentRequested(true)
    , referencePoint(Base::Vector2d(0., 0.))
    , lastMouseAngle(0.0)
{
    // Create parameter observer and initialise watched parameters
    pObserver = std::make_unique<SnapManager::ParameterObserver>(*this);
}

SnapManager::~SnapManager()
{}

Base::Vector2d SnapManager::snap(Base::Vector2d inputPos, SnapType mask)
{
    lastKeyPointSnap = KeyPointSnap();

    // Prumo 3D: pontos-ímã. Os marcadores aparecem enquanto uma ferramenta de desenho está ativa;
    // o ponto mais próximo captura o cursor, exceto quando um vértice já está pré-selecionado
    // (o vértice existente tem prioridade e gera a restrição de coincidência).
    const bool wantsPoints = (static_cast<int>(mask) & static_cast<int>(SnapType::Point)) != 0;
    const bool handlerActive = ViewProviderSketchSnapAttorney::isHandlerActive(viewProvider);
    KeyPointSnap keyPoint;
    bool keyPointFound = false;
    if (snapRequested && snapToObjectsRequested && snapToKeyPointsRequested && wantsPoints) {
        keyPointFound = findKeyPoint(inputPos, handlerActive, keyPoint);
    }
    else {
        clearKeyPointMarkers();
    }

    if (!snapRequested) {
        clearAlignmentLines();
        return inputPos;
    }

    Base::Vector2d snapPos = inputPos;

    // In order of priority:

    // 1 - Snap at an angle
    if ((static_cast<int>(mask) & static_cast<int>(SnapType::Angle)) && angleSnapRequested
        && QApplication::keyboardModifiers() == Qt::ControlModifier
        && snapAtAngle(inputPos, snapPos)) {
        clearAlignmentLines();
        return snapPos;
    }
    else {
        lastMouseAngle = 0.0;
    }

    // 2a - Prumo 3D: ponto-ímã (quadrante, ponto médio, interseção)
    if (keyPointFound) {
        const int VtId = ViewProviderSketchSnapAttorney::getPreselectPoint(viewProvider);
        const int CrsId = ViewProviderSketchSnapAttorney::getPreselectCross(viewProvider);
        if (VtId < 0 && CrsId != 0) {
            lastKeyPointSnap = keyPoint;
            clearAlignmentLines();
            return keyPoint.pos;
        }
    }

    // 2b - Prumo 3D: linhas de inferência — alinhamento com pontos existentes, só quando nada está
    // pré-selecionado (com o cursor sobre uma curva ou ponto, valem o snap normal e as restrições)
    {
        const int VtId = ViewProviderSketchSnapAttorney::getPreselectPoint(viewProvider);
        const int CrsId = ViewProviderSketchSnapAttorney::getPreselectCross(viewProvider);
        const int CrvId = ViewProviderSketchSnapAttorney::getPreselectCurve(viewProvider);
        const bool nadaPreselecionado = VtId < 0 && CrsId < 0 && CrvId > Sketcher::GeoEnum::RefExt
            && CrvId < 0;
        Base::Vector2d alinhado = inputPos;
        if (snapToObjectsRequested && snapToAlignmentRequested && wantsPoints && handlerActive
            && nadaPreselecionado && !keyPointFound
            && snapToAlignment(inputPos, alinhado, handlerActive)) {
            return alinhado;
        }
        clearAlignmentLines();
    }

    // 2 - Snap to objects (may partially snap to axis, leaving other coordinate for grid)
    bool snappedToObject = false;
    if ((static_cast<int>(mask)
         & (static_cast<int>(SnapType::Point) | static_cast<int>(SnapType::Edge)))
        && snapToObjectsRequested) {
        snappedToObject = snapToObject(inputPos, snapPos, mask);
        if (snappedToObject) {
            return snapPos;  // Full snap (point or curve) - done
        }
        // if false was returned but snapPos was modified (axis case), continue to grid snap
    }

    // 3 - Snap to grid (will work on coordinates not already locked by axis snap)
    if ((static_cast<int>(mask) & static_cast<int>(SnapType::Grid)) && snapToGridRequested
        /*&& viewProvider.ShowGrid.getValue() */) {  // Snap to grid is enabled
                                                     // even if the grid is not visible.

        // use snapPos as input (which may have one coordinate locked by axis)
        Base::Vector2d gridSnapResult = snapPos;
        if (snapToGrid(snapPos, gridSnapResult)) {
            return gridSnapResult;
        }
        // if grid snap happened, return the result which combines axis + grid
        // if axis locked a coordinate, snapPos already had it, and grid snap respected it
        return snapPos;
    }

    return snapPos;
}

bool SnapManager::snapAtAngle(Base::Vector2d inputPos, Base::Vector2d& snapPos)
{
    double length = (inputPos - referencePoint).Length();

    double angle1 = (inputPos - referencePoint).Angle();
    double angle2 = angle1 + (angle1 < 0. ? 2 : -2) * std::numbers::pi;
    lastMouseAngle = abs(angle1 - lastMouseAngle) < abs(angle2 - lastMouseAngle) ? angle1 : angle2;

    double angle = round(lastMouseAngle / snapAngle) * snapAngle;
    snapPos = referencePoint + length * Base::Vector2d(cos(angle), sin(angle));

    return true;
}

bool SnapManager::snapToObject(Base::Vector2d inputPos, Base::Vector2d& snapPos, SnapType mask)
{
    Sketcher::SketchObject* Obj = viewProvider.getSketchObject();
    int geoId = GeoEnum::GeoUndef;
    Sketcher::PointPos posId = Sketcher::PointPos::none;

    int VtId = ViewProviderSketchSnapAttorney::getPreselectPoint(viewProvider);
    int CrsId = ViewProviderSketchSnapAttorney::getPreselectCross(viewProvider);
    int CrvId = ViewProviderSketchSnapAttorney::getPreselectCurve(viewProvider);

    if ((static_cast<int>(mask) & static_cast<int>(SnapType::Point)) && (CrsId == 0 || VtId >= 0)) {
        if (CrsId == 0) {
            geoId = Sketcher::GeoEnum::RtPnt;
            posId = Sketcher::PointPos::start;
        }
        else if (VtId >= 0) {
            Obj->getGeoVertexIndex(VtId, geoId, posId);
        }

        snapPos.x = Obj->getPoint(geoId, posId).x;
        snapPos.y = Obj->getPoint(geoId, posId).y;
        return true;
    }
    else if (static_cast<int>(mask) & static_cast<int>(SnapType::Edge)) {
        if (CrsId == 1) {  // H_Axis
            snapPos.y = 0;
            // dont return true, allow grid snap to handle X coordinate
            return false;
        }
        else if (CrsId == 2) {  // V_Axis
            snapPos.x = 0;
            // dont return true, allow grid snap to handle Y coordinate
            return false;
        }
        else if (CrvId >= 0 || CrvId <= Sketcher::GeoEnum::RefExt) {  // Curves

            const Part::Geometry* geo = Obj->getGeometry(CrvId);

            Base::Vector3d pointToOverride(inputPos.x, inputPos.y, 0.);

            double pointParam = 0.0;
            auto curve = dynamic_cast<const Part::GeomCurve*>(geo);
            if (curve) {
                try {
                    curve->closestParameter(pointToOverride, pointParam);
                    pointToOverride = curve->pointAtParameter(pointParam);
                }
                catch (Base::CADKernelError& e) {
                    e.reportException();
                    return false;
                }

                // If it is a line, then we check if we need to snap to the middle.
                if (geo->is<Part::GeomLineSegment>()) {
                    const Part::GeomLineSegment* line = static_cast<const Part::GeomLineSegment*>(geo);
                    snapToLineMiddle(pointToOverride, line);
                }

                // If it is an arc, then we check if we need to snap to the middle (not the center).
                if (geo->is<Part::GeomArcOfCircle>()) {
                    const Part::GeomArcOfCircle* arc = static_cast<const Part::GeomArcOfCircle*>(geo);
                    snapToArcMiddle(pointToOverride, arc);
                }

                snapPos.x = pointToOverride.x;
                snapPos.y = pointToOverride.y;

                return true;
            }
        }
    }
    return false;
}

bool SnapManager::snapToGrid(Base::Vector2d inputPos, Base::Vector2d& snapPos)
{
    // Snap Tolerance in pixels
    const double snapTol = viewProvider.getGridSize() / 5;

    snapPos = inputPos;

    double tmpX = inputPos.x, tmpY = inputPos.y;

    viewProvider.getClosestGridPoint(tmpX, tmpY);

    bool snapped = false;

    // Check if x within snap tolerance
    if (inputPos.x < tmpX + snapTol && inputPos.x > tmpX - snapTol) {
        snapPos.x = tmpX;  // Snap X Mouse Position
        snapped = true;
    }

    // Check if y within snap tolerance
    if (inputPos.y < tmpY + snapTol && inputPos.y > tmpY - snapTol) {
        snapPos.y = tmpY;  // Snap Y Mouse Position
        snapped = true;
    }

    return snapped;
}

bool SnapManager::snapToLineMiddle(Base::Vector3d& pointToOverride, const Part::GeomLineSegment* line)
{
    Base::Vector3d startPoint = line->getStartPoint();
    Base::Vector3d endPoint = line->getEndPoint();
    Base::Vector3d midPoint = (startPoint + endPoint) / 2;

    // Check if we are at middle of the line and if so snap to it.
    if ((pointToOverride - midPoint).Length() < (endPoint - startPoint).Length() * 0.05) {
        pointToOverride = midPoint;
        return true;
    }

    return false;
}

bool SnapManager::snapToArcMiddle(Base::Vector3d& pointToOverride, const Part::GeomArcOfCircle* arc)
{
    Base::Vector3d centerPoint = arc->getCenter();
    Base::Vector3d startVec = (arc->getStartPoint() - centerPoint);
    Base::Vector3d middleVec = startVec + (arc->getEndPoint() - centerPoint);

    /* Handle the case of arc angle = 180 */
    if (middleVec.Length() < Precision::Confusion()) {
        middleVec.x = startVec.y;
        middleVec.y = -startVec.x;
    }
    else {
        middleVec = middleVec / middleVec.Length() * arc->getRadius();
    }

    Base::Vector2d mVec = Base::Vector2d(middleVec.x, middleVec.y);
    Base::Vector3d pointVec = pointToOverride - centerPoint;
    Base::Vector2d pVec = Base::Vector2d(pointVec.x, pointVec.y);

    double u, v;
    arc->getRange(u, v, true);
    if (v < u) {
        v += 2 * std::numbers::pi;
    }
    double angle = v - u;
    int revert = angle < std::numbers::pi ? 1 : -1;

    /*To know if we are close to the middle of the arc, we are going to compare the angle of the
     * (mouse cursor - center) to the angle of the middle of the arc. If it's less than 10% of the
     * arc angle, then we snap.
     */
    if (fabs(pVec.Angle() - (revert * mVec).Angle()) < 0.10 * angle) {
        pointToOverride = centerPoint + middleVec * revert;
        return true;
    }

    return false;
}

void SnapManager::setAngleSnapping(bool enable, Base::Vector2d referencepoint)
{
    angleSnapRequested = enable;
    referencePoint = referencepoint;
}

Base::Vector2d SketcherGui::SnapManager::SnapHandle::compute(SnapType mask)
{
    if (!mgr) {
        return cursorPos;
    }
    return mgr->snap(cursorPos, mask);
}

/********************** Prumo 3D: pontos-ímã (quadrantes, médios, interseções) ******************/

namespace
{

struct NearCurve
{
    int geoId;
    const Part::GeomCurve* curve;
    double distance;
};

struct KeyCandidate
{
    Base::Vector2d pos;
    KeyPointKind kind;
    int geoId1;
    int geoId2;
};

double distanceToCurve(const Part::GeomCurve* curve, const Base::Vector2d& pos, double tol)
{
    // Prumo: atalhos analíticos/limites inferiores para não projetar (OCC) em cada curva do esboço
    // a cada movimento do mouse; só curvas que podem estar a menos de tol seguem para a projeção.
    const double longe = std::numeric_limits<double>::max();
    if (const auto* seg = dynamic_cast<const Part::GeomLineSegment*>(curve)) {
        const Base::Vector3d a3 = seg->getStartPoint();
        const Base::Vector3d b3 = seg->getEndPoint();
        const Base::Vector2d a(a3.x, a3.y);
        const Base::Vector2d ab(b3.x - a3.x, b3.y - a3.y);
        const double len2 = ab.x * ab.x + ab.y * ab.y;
        double t = len2 > 0 ? ((pos.x - a.x) * ab.x + (pos.y - a.y) * ab.y) / len2 : 0.;
        t = std::clamp(t, 0., 1.);
        return Base::Vector2d(a.x + t * ab.x - pos.x, a.y + t * ab.y - pos.y).Length();
    }
    if (const auto* conic = dynamic_cast<const Part::GeomConic*>(curve)) {
        const Base::Vector3d c = conic->getCenter();
        const double dc = Base::Vector2d(pos.x - c.x, pos.y - c.y).Length();
        if (const auto* circ = dynamic_cast<const Part::GeomCircle*>(curve)) {
            if (std::abs(dc - circ->getRadius()) > tol) {
                return longe;
            }
        }
        else if (const auto* arc = dynamic_cast<const Part::GeomArcOfCircle*>(curve)) {
            if (std::abs(dc - arc->getRadius()) > tol) {
                return longe;
            }
        }
        else if (const auto* el = dynamic_cast<const Part::GeomEllipse*>(curve)) {
            if (dc - el->getMajorRadius() > tol || el->getMinorRadius() - dc > tol) {
                return longe;
            }
        }
        else if (const auto* ael = dynamic_cast<const Part::GeomArcOfEllipse*>(curve)) {
            if (dc - ael->getMajorRadius() > tol || ael->getMinorRadius() - dc > tol) {
                return longe;
            }
        }
    }
    else if (const auto* bs = dynamic_cast<const Part::GeomBSplineCurve*>(curve)) {
        // a curva fica dentro do fecho convexo dos polos: caixa dos polos + tol
        const std::vector<Base::Vector3d> poles = bs->getPoles();
        if (!poles.empty()) {
            double x0 = poles[0].x, x1 = x0, y0 = poles[0].y, y1 = y0;
            for (const auto& q : poles) {
                x0 = std::min(x0, q.x);
                x1 = std::max(x1, q.x);
                y0 = std::min(y0, q.y);
                y1 = std::max(y1, q.y);
            }
            if (pos.x < x0 - tol || pos.x > x1 + tol || pos.y < y0 - tol || pos.y > y1 + tol) {
                return longe;
            }
        }
    }
    try {
        Base::Vector3d p(pos.x, pos.y, 0.);
        double u = 0.;
        if (!curve->closestParameter(p, u)) {
            return std::numeric_limits<double>::max();
        }
        Base::Vector3d q = curve->pointAtParameter(u);
        return Base::Vector2d(q.x - pos.x, q.y - pos.y).Length();
    }
    catch (const Base::Exception&) {
        return std::numeric_limits<double>::max();
    }
    catch (const Standard_Failure&) {
        return std::numeric_limits<double>::max();
    }
}

/// true se o ângulo a (rad) está dentro do intervalo [u, v] de um arco (sentido anti-horário)
bool angleInArc(double a, double u, double v)
{
    const double twoPi = 2 * std::numbers::pi;
    double span = v - u;
    while (span < 0) {
        span += twoPi;
    }
    double d = a - u;
    while (d < 0) {
        d += twoPi;
    }
    while (d >= twoPi) {
        d -= twoPi;
    }
    return d <= span + 1e-9;
}

void addCurveKeyPoints(int geoId, const Part::GeomCurve* curve, std::vector<KeyCandidate>& out)
{
    using std::numbers::pi;
    auto add = [&](const Base::Vector3d& p, KeyPointKind kind) {
        out.push_back({Base::Vector2d(p.x, p.y), kind, geoId, Sketcher::GeoEnum::GeoUndef});
    };

    if (curve->is<Part::GeomCircle>()) {
        auto* circle = static_cast<const Part::GeomCircle*>(curve);
        const Base::Vector3d c = circle->getCenter();
        const double r = circle->getRadius();
        for (int k = 0; k < 4; ++k) {
            const double a = k * pi / 2;
            add(c + Base::Vector3d(r * std::cos(a), r * std::sin(a), 0.), KeyPointKind::Quadrant);
        }
    }
    else if (curve->is<Part::GeomArcOfCircle>()) {
        auto* arc = static_cast<const Part::GeomArcOfCircle*>(curve);
        const Base::Vector3d c = arc->getCenter();
        const double r = arc->getRadius();
        double u = 0., v = 0.;
        arc->getRange(u, v, /*emulateCCWXY=*/true);
        for (int k = 0; k < 4; ++k) {
            const double a = k * pi / 2;
            if (angleInArc(a, u, v)) {
                add(c + Base::Vector3d(r * std::cos(a), r * std::sin(a), 0.), KeyPointKind::Quadrant);
            }
        }
        // ponto médio do arco
        double m = u + (v < u ? v + 2 * pi - u : v - u) / 2;
        add(c + Base::Vector3d(r * std::cos(m), r * std::sin(m), 0.), KeyPointKind::Midpoint);
    }
    else if (curve->is<Part::GeomEllipse>()) {
        auto* ellipse = static_cast<const Part::GeomEllipse*>(curve);
        const Base::Vector3d c = ellipse->getCenter();
        Base::Vector3d major = ellipse->getMajorAxisDir();
        major.Normalize();
        const Base::Vector3d minor(-major.y, major.x, 0.);
        const double a = ellipse->getMajorRadius();
        const double b = ellipse->getMinorRadius();
        add(c + major * a, KeyPointKind::AxisVertex);
        add(c - major * a, KeyPointKind::AxisVertex);
        add(c + minor * b, KeyPointKind::AxisVertex);
        add(c - minor * b, KeyPointKind::AxisVertex);
    }
    else if (curve->is<Part::GeomLineSegment>()) {
        auto* line = static_cast<const Part::GeomLineSegment*>(curve);
        add((line->getStartPoint() + line->getEndPoint()) / 2, KeyPointKind::Midpoint);
    }
}

/// extremidades de uma curva limitada (para não repetir como interseção um vértice que já existe)
bool isCurveEndpoint(const Part::GeomCurve* curve, const Base::Vector3d& p, double tol)
{
    auto* bounded = dynamic_cast<const Part::GeomBoundedCurve*>(curve);
    if (!bounded) {
        return false;
    }
    return (bounded->getStartPoint() - p).Length() < tol || (bounded->getEndPoint() - p).Length() < tol;
}

}  // namespace

bool SnapManager::findKeyPoint(Base::Vector2d inputPos, bool showMarkers, KeyPointSnap& found)
{
    found = KeyPointSnap();

    Sketcher::SketchObject* obj = viewProvider.getSketchObject();
    if (!obj) {
        clearKeyPointMarkers();
        return false;
    }

    // Tolerâncias proporcionais ao zoom (getScaleFactor ~ 3 % da altura da vista)
    const double scale = viewProvider.getScaleFactor();
    const double captureTol = 0.5 * scale;  // captura do cursor
    const double showTol = 2.5 * scale;     // marcadores visíveis ao redor do cursor
    const double confusion = 1e-7;

    // 1) curvas perto do cursor (geometria do esboço e geometria externa; eixos ficam de fora)
    std::vector<NearCurve> nearCurves;
    auto consider = [&](int geoId) {
        const Part::Geometry* geo = obj->getGeometry(geoId);
        auto* curve = dynamic_cast<const Part::GeomCurve*>(geo);
        if (!curve) {
            return;
        }
        const double d = distanceToCurve(curve, inputPos, showTol);
        if (d < showTol) {
            nearCurves.push_back({geoId, curve, d});
        }
    };
    for (int i = 0; i <= obj->getHighestCurveIndex(); ++i) {
        consider(i);
    }
    for (int k = 2; k < obj->getExternalGeometryCount(); ++k) {
        consider(Sketcher::GeoEnum::RefExt - (k - 2));
    }

    constexpr std::size_t maxCurves = 12;
    std::sort(nearCurves.begin(), nearCurves.end(), [](const NearCurve& a, const NearCurve& b) {
        return a.distance < b.distance;
    });
    if (nearCurves.size() > maxCurves) {
        nearCurves.resize(maxCurves);
    }

    // 2) pontos notáveis de cada curva e interseções entre elas
    std::vector<KeyCandidate> candidates;
    for (const auto& nc : nearCurves) {
        addCurveKeyPoints(nc.geoId, nc.curve, candidates);
    }
    for (std::size_t i = 0; i < nearCurves.size(); ++i) {
        for (std::size_t j = i + 1; j < nearCurves.size(); ++j) {
            std::vector<std::pair<Base::Vector3d, Base::Vector3d>> points;
            try {
                nearCurves[i].curve->intersect(nearCurves[j].curve, points, Precision::Confusion());
            }
            catch (const Base::Exception&) {
                continue;
            }
            catch (const Standard_Failure&) {
                continue;
            }
            for (const auto& pr : points) {
                const Base::Vector3d& p = pr.first;
                if (isCurveEndpoint(nearCurves[i].curve, p, captureTol * 0.1)
                    || isCurveEndpoint(nearCurves[j].curve, p, captureTol * 0.1)) {
                    continue;  // já é um vértice: o snap a vértices cuida dele
                }
                candidates.push_back(
                    {Base::Vector2d(p.x, p.y),
                     KeyPointKind::Intersection,
                     nearCurves[i].geoId,
                     nearCurves[j].geoId}
                );
            }
        }
    }

    // 3) filtra os visíveis, remove repetidos e escolhe o mais próximo dentro da captura
    std::vector<Base::Vector2d> markers;
    std::vector<KeyCandidate> visible;
    for (const auto& c : candidates) {
        if ((c.pos - inputPos).Length() > showTol) {
            continue;
        }
        bool duplicate = false;
        for (auto& v : visible) {
            if ((v.pos - c.pos).Length() < confusion + captureTol * 0.02) {
                // interseção tem prioridade sobre quadrante/médio no mesmo lugar
                if (c.kind == KeyPointKind::Intersection && v.kind != KeyPointKind::Intersection) {
                    v = c;
                }
                duplicate = true;
                break;
            }
        }
        if (!duplicate) {
            visible.push_back(c);
        }
    }

    int active = -1;
    double best = captureTol;
    for (std::size_t i = 0; i < visible.size(); ++i) {
        markers.push_back(visible[i].pos);
        const double d = (visible[i].pos - inputPos).Length();
        if (d < best) {
            best = d;
            active = static_cast<int>(i);
        }
    }

    if (showMarkers && !markers.empty()) {
        ViewProviderSketchSnapAttorney::drawSnapMarkers(viewProvider, markers, active);
        keyPointMarkersShown = true;
    }
    else {
        clearKeyPointMarkers();
    }

    if (active < 0) {
        return false;
    }

    const auto& c = visible[active];
    found.valid = true;
    found.pos = c.pos;
    found.kind = c.kind;
    found.geoId1 = c.geoId1;
    found.geoId2 = c.geoId2;
    return true;
}

void SnapManager::clearKeyPointMarkers()
{
    if (!keyPointMarkersShown) {
        return;
    }
    keyPointMarkersShown = false;
    ViewProviderSketchSnapAttorney::drawSnapMarkers(viewProvider, {}, -1);
}

/********************** Prumo 3D: linhas de inferência (alinhamento H/V) ************************/

bool SnapManager::snapToAlignment(Base::Vector2d inputPos, Base::Vector2d& snapPos, bool showLines)
{
    Sketcher::SketchObject* obj = viewProvider.getSketchObject();
    if (!obj) {
        clearAlignmentLines();
        return false;
    }
    const double scale = viewProvider.getScaleFactor();
    const double captureTol = 0.3 * scale;  // um pouco menor que a dos pontos-ímã

    // pontos de referência: extremidades, centros e pontos médios de retas, da geometria do esboço
    // e da geometria externa (inclui a origem; os eixos H/V ficam de fora)
    std::vector<Base::Vector2d> pontos;
    pontos.emplace_back(0.0, 0.0);
    std::vector<int> geoIds;
    for (int i = 0; i <= obj->getHighestCurveIndex(); ++i) {
        geoIds.push_back(i);
    }
    for (int k = 2; k < obj->getExternalGeometryCount(); ++k) {
        geoIds.push_back(Sketcher::GeoEnum::RefExt - (k - 2));
    }
    for (int geoId : geoIds) {
        if (pontos.size() >= 4000) {
            break;
        }
        const Part::Geometry* geo = obj->getGeometry(geoId);
        if (!geo) {
            continue;
        }
        for (auto pos : {Sketcher::PointPos::start, Sketcher::PointPos::end, Sketcher::PointPos::mid}) {
            try {
                Base::Vector3d p = obj->getPoint(geoId, pos);
                if (std::isfinite(p.x) && std::isfinite(p.y)) {
                    pontos.emplace_back(p.x, p.y);
                }
            }
            catch (const Base::Exception&) {
            }
        }
        if (const auto* seg = dynamic_cast<const Part::GeomLineSegment*>(geo)) {
            const Base::Vector3d m = (seg->getStartPoint() + seg->getEndPoint()) / 2.0;
            pontos.emplace_back(m.x, m.y);
        }
    }

    // ponto mais próximo em X (linha vertical) e em Y (linha horizontal), dentro da captura
    int iv = -1;
    int ih = -1;
    double dv = captureTol;
    double dh = captureTol;
    for (int k = 0; k < static_cast<int>(pontos.size()); ++k) {
        const auto& p = pontos[k];
        if ((p - inputPos).Length() < captureTol) {
            continue;  // em cima do ponto: isso é snap de vértice, não alinhamento
        }
        const double ex = std::fabs(p.x - inputPos.x);
        const double ey = std::fabs(p.y - inputPos.y);
        if (ex < dv) {
            dv = ex;
            iv = k;
        }
        if (ey < dh) {
            dh = ey;
            ih = k;
        }
    }
    if (iv < 0 && ih < 0) {
        clearAlignmentLines();
        return false;
    }
    snapPos = inputPos;
    if (iv >= 0) {
        snapPos.x = pontos[iv].x;
    }
    if (ih >= 0) {
        snapPos.y = pontos[ih].y;
    }
    if (showLines) {
        std::vector<Base::Vector2d> seg;
        if (iv >= 0) {
            seg.push_back(pontos[iv]);
            seg.push_back(snapPos);
        }
        if (ih >= 0) {
            seg.push_back(pontos[ih]);
            seg.push_back(snapPos);
        }
        ViewProviderSketchSnapAttorney::drawSnapAlignment(viewProvider, seg);
        alignmentLinesShown = true;
    }
    return true;
}

void SnapManager::clearAlignmentLines()
{
    if (!alignmentLinesShown) {
        return;
    }
    alignmentLinesShown = false;
    ViewProviderSketchSnapAttorney::drawSnapAlignment(viewProvider, {});
}
