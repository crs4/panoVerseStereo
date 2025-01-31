import numpy as np
from scipy.ndimage import map_coordinates
from scipy.spatial.distance import pdist, squareform
##from sklearn.decomposition import PCA

##MINE
import cv2

PI = float(np.pi)


def fuv2img(fuv, coorW=1024, floorW=1024, floorH=512):
    '''
    Project 1d signal in uv space to 2d floor plane image
    '''
    floor_plane_x, floor_plane_y = np.meshgrid(range(floorW), range(floorH))
    floor_plane_x, floor_plane_y = -(floor_plane_y - floorH / 2), floor_plane_x - floorW / 2
    floor_plane_coridx = (np.arctan2(floor_plane_y, floor_plane_x) / (2 * PI) + 0.5) * coorW - 0.5
    floor_plane = map_coordinates(fuv, floor_plane_coridx.reshape(1, -1), order=1, mode='wrap')
    floor_plane = floor_plane.reshape(floorH, floorW)
    return floor_plane


def np_coorx2u(coorx, coorW=1024):
    return ((coorx + 0.5) / coorW - 0.5) * 2 * PI


def np_coory2v(coory, coorH=512):
    return -((coory + 0.5) / coorH - 0.5) * PI

#####MINE transform
def np_coor2xy(coor, z=50, coorW=1024, coorH=512, floorW=1024, floorH=512, m_ratio = 1.0):
    '''
    coor: N x 2, index of array in (col, row) format eg. 1024x2
    m_ratio: pixel/cm ratio for tensor fitting
    '''           
    coor = np.array(coor)
    u = np_coorx2u(coor[:, 0], coorW)       
    v = np_coory2v(coor[:, 1], coorH)
                  
    c = z / np.tan(v)
    x = m_ratio * c * np.sin(u) + floorW / 2.0 - 0.5
    y = -m_ratio *c * np.cos(u) + floorH / 2.0 - 0.5
    
    return np.hstack([x[:, None], y[:, None]])

####NB same of E2P/A2P for coords
def np_coor2ud(coor, z, coorW, coorH, m_ratio = 1.0):
    '''
    coor: N x 2, index of array in (col, row) format eg. 1024x2
    m_ratio: pixel/cm ratio for tensor fitting
    '''           
    coor = np.array(coor)
    u = np_coorx2u(coor[:, 0], coorW)       
    v = np_coory2v(coor[:, 1], coorH)
                  
    d = m_ratio * (np.absolute(z / np.tan(v)))
    
    return u,d

def ud2xy(u, d, floorW=1024, floorH=512, use_offset = False):     
    os_x = 0.0    
    if(use_offset):
      os_x = float(floorW)
    x =   d * np.sin(u) + floorW / 2 - 0.5 + os_x
    y = - d * np.cos(u) + floorH / 2 - 0.5
    
    return np.hstack([x[:, None], y[:, None]])

def np_x_u_solve_y(x, u, floorW=1024, floorH=512):
    c = (x - floorW / 2 + 0.5) / np.sin(u)
    return -c * np.cos(u) + floorH / 2 - 0.5


def np_y_u_solve_x(y, u, floorW=1024, floorH=512):
    c = -(y - floorH / 2 + 0.5) / np.cos(u)
    return c * np.sin(u) + floorW / 2 - 0.5


def np_xy2coor(xy, z=50, coorW=1024, coorH=512, floorW=1024, floorH=512):
    '''
    xy: N x 2
    '''
    x = xy[:, 0] - floorW / 2 + 0.5
    y = xy[:, 1] - floorH / 2 + 0.5

    u = np.arctan2(x, -y)
    v = np.arctan(z / np.sqrt(x**2 + y**2))

    coorx = (u / (2 * PI) + 0.5) * coorW - 0.5
    coory = (-v / PI + 0.5) * coorH - 0.5

    return np.hstack([coorx[:, None], coory[:, None]])


def mean_percentile(vec, p1=25, p2=75):
    vmin = np.percentile(vec, p1)
    vmax = np.percentile(vec, p2)
    return vec[(vmin <= vec) & (vec <= vmax)].mean()


def vote(vec, tol):
    vec = np.sort(vec)
    n = np.arange(len(vec))[::-1]
    n = n[:, None] - n[None, :] + 1.0
    l = squareform(pdist(vec[:, None], 'minkowski', p=1) + 1e-9)

    invalid = (n < len(vec) * 0.4) | (l > tol)
    if (~invalid).sum() == 0 or len(vec) < tol:
        best_fit = np.median(vec)
        p_score = 0
    else:
        l[invalid] = 1e5
        n[invalid] = -1
        score = n
        max_idx = score.argmax()
        max_row = max_idx // len(vec)
        max_col = max_idx % len(vec)
        assert max_col > max_row
        best_fit = vec[max_row:max_col+1].mean()
        p_score = (max_col - max_row + 1) / len(vec)

    l1_score = np.abs(vec - best_fit).mean()

    return best_fit, p_score, l1_score


def get_z1(coory0, coory1, z0=50, coorH=512):
    v0 = np_coory2v(coory0, coorH)
    v1 = np_coory2v(coory1, coorH)
    c0 = z0 / np.tan(v0)
    z1 = c0 * np.tan(v1)
    return z1

def get_z1_mean(coory0, coory1, z0=50, coorH=512):
    v0 = np_coory2v(coory0, coorH)
    v1 = np_coory2v(coory1, coorH)
    c0 = z0 / np.tan(v0)
    z1 = c0 * np.tan(v1)

    z1_mean = mean_percentile(z1)

    return z1_mean

def get_z_ceiling_mean(coory0, coory1, z_floor, coorH):
    vc = np_coory2v(coory0, coorH)
    vf = np_coory2v(coory1, coorH)
    cc = z_floor / np.tan(vf)
    z_ceiling = cc * np.tan(vc)
    z_ceiling_mean = mean_percentile(z_ceiling)

    return z_ceiling_mean

def np_refine_by_fix_z(coory0, coory1, z0=50, coorH=512):
    '''
    Refine coory1 by coory0
    coory0 are assumed on given plane z
    '''
    v0 = np_coory2v(coory0, coorH)
    v1 = np_coory2v(coory1, coorH)

    c0 = z0 / np.tan(v0)
    z1 = c0 * np.tan(v1)
    z1_mean = mean_percentile(z1)
    v1_refine = np.arctan2(z1_mean, c0)
    coory1_refine = (-v1_refine / PI + 0.5) * coorH - 0.5

    return coory1_refine, z1_mean


def infer_coory(coory0, h, z0=50, coorH=512):
    v0 = np_coory2v(coory0, coorH)
    c0 = z0 / np.tan(v0)
    z1 = z0 + h
    v1 = np.arctan2(z1, c0)
    return (-v1 / PI + 0.5) * coorH - 0.5


def get_gpid(coorx, coorW):
    gpid = np.zeros(coorW)
    gpid[np.round(coorx).astype(int)] = 1
    gpid = np.cumsum(gpid).astype(int)
    gpid[gpid == gpid[-1]] = 0
    return gpid


def get_gpid_idx(gpid, j):
    idx = np.where(gpid == j)[0]
    if idx[0] == 0 and idx[-1] != len(idx) - 1:
        _shift = -np.where(idx != np.arange(len(idx)))[0][0]
        idx = np.roll(idx, _shift)
    return idx


def gpid_two_split(xy, tpid_a, tpid_b):
    m = np.arange(len(xy)) + 1
    cum_a = np.cumsum(xy[:, tpid_a])
    cum_b = np.cumsum(xy[::-1, tpid_b])
    l1_a = cum_a / m - cum_a / (m * m)
    l1_b = cum_b / m - cum_b / (m * m)
    l1_b = l1_b[::-1]

    score = l1_a[:-1] + l1_b[1:]
    best_split = score.argmax() + 1

    va = xy[:best_split, tpid_a].mean()
    vb = xy[best_split:, tpid_b].mean()

    return va, vb


def _get_rot_rad(px, py):
    if px < 0:
        px, py = -px, -py
    rad = np.arctan2(py, px) * 180 / np.pi
    if rad > 45:
        return 90 - rad
    if rad < -45:
        return -90 - rad
    return -rad


def get_rot_rad(init_coorx, coory, z=50, coorW=1024, coorH=512, floorW=1024, floorH=512, tol=5):
    gpid = get_gpid(init_coorx, coorW)
    coor = np.hstack([np.arange(coorW)[:, None], coory[:, None]])
    xy = np_coor2xy(coor, z, coorW, coorH, floorW, floorH)
    xy_cor = []

    rot_rad_suggestions = []
    for j in range(len(init_coorx)):
        pca = PCA(n_components=1)
        pca.fit(xy[gpid == j])
        rot_rad_suggestions.append(_get_rot_rad(*pca.components_[0]))
    rot_rad_suggestions = np.sort(rot_rad_suggestions + [1e9])

    rot_rad = np.mean(rot_rad_suggestions[:-1])
    best_rot_rad_sz = -1
    last_j = 0
    for j in range(1, len(rot_rad_suggestions)):
        if rot_rad_suggestions[j] - rot_rad_suggestions[j-1] > tol:
            last_j = j
        elif j - last_j > best_rot_rad_sz:
            rot_rad = rot_rad_suggestions[last_j:j+1].mean()
            best_rot_rad_sz = j - last_j

    dx = int(round(rot_rad * 1024 / 360))
    return dx, rot_rad


def gen_ww_cuboid(xy, gpid, tol):
    xy_cor = []
    assert len(np.unique(gpid)) == 4

    # For each part seperated by wall-wall peak, voting for a wall
    for j in range(4):
        now_x = xy[gpid == j, 0]
        now_y = xy[gpid == j, 1]
        new_x, x_score, x_l1 = vote(now_x, tol)
        new_y, y_score, y_l1 = vote(now_y, tol)
        if (x_score, -x_l1) > (y_score, -y_l1):
            xy_cor.append({'type': 0, 'val': new_x, 'score': x_score})
        else:
            xy_cor.append({'type': 1, 'val': new_y, 'score': y_score})

    # Sanity fallback
    scores = [0, 0]
    for j in range(4):
        if xy_cor[j]['type'] == 0:
            scores[j % 2] += xy_cor[j]['score']
        else:
            scores[j % 2] -= xy_cor[j]['score']
    if scores[0] > scores[1]:
        xy_cor[0]['type'] = 0
        xy_cor[1]['type'] = 1
        xy_cor[2]['type'] = 0
        xy_cor[3]['type'] = 1
    else:
        xy_cor[0]['type'] = 1
        xy_cor[1]['type'] = 0
        xy_cor[2]['type'] = 1
        xy_cor[3]['type'] = 0

    return xy_cor


def gen_ww_general(init_coorx, xy, gpid, tol):
    ####input: N corners as equi horizontal pos, 1024x2 XY coords of the ceiling boundary, 
    xy_cor = []
    assert len(init_coorx) == len(np.unique(gpid))

    print('debugging post_proc gen_ww_general')
        
    # Candidate for each part seperated by wall-wall boundary
    for j in range(len(init_coorx)):
        now_x = xy[gpid == j, 0]
        now_y = xy[gpid == j, 1]
                
        new_x, x_score, x_l1 = vote(now_x, tol)
        new_y, y_score, y_l1 = vote(now_y, tol)
        u0 = np_coorx2u(init_coorx[(j - 1 + len(init_coorx)) % len(init_coorx)])
        u1 = np_coorx2u(init_coorx[j])
                
        if (x_score, -x_l1) > (y_score, -y_l1):
            ##print(j, 'type 0')
            xy_cor.append({'type': 0, 'val': new_x, 'score': x_score, 'action': 'ori', 'gpid': j, 'u0': u0, 'u1': u1, 'tbd': True})
        else:
            ##print(j, 'type 1')
            xy_cor.append({'type': 1, 'val': new_y, 'score': y_score, 'action': 'ori', 'gpid': j, 'u0': u0, 'u1': u1, 'tbd': True})

    ##print(xy_cor)

    # Construct wall from highest score to lowest
    while True:
        # Finding undetermined wall with highest score
        tbd = -1
        for i in range(len(xy_cor)):
            if xy_cor[i]['tbd'] and (tbd == -1 or xy_cor[i]['score'] > xy_cor[tbd]['score']):
                tbd = i
        if tbd == -1:
            break

        # This wall is determined
        xy_cor[tbd]['tbd'] = False
        p_idx = (tbd - 1 + len(xy_cor)) % len(xy_cor)
        n_idx = (tbd + 1) % len(xy_cor)

        num_tbd_neighbor = xy_cor[p_idx]['tbd'] + xy_cor[n_idx]['tbd']

        # Two adjacency walls are not determined yet => not special case
        if num_tbd_neighbor == 2:
            continue

        # Only one of adjacency two walls is determine => add now or later special case
        if num_tbd_neighbor == 1:
            if (not xy_cor[p_idx]['tbd'] and xy_cor[p_idx]['type'] == xy_cor[tbd]['type']) or\
                    (not xy_cor[n_idx]['tbd'] and xy_cor[n_idx]['type'] == xy_cor[tbd]['type']):
                # Current wall is different from one determined adjacency wall
                if xy_cor[tbd]['score'] >= -1:
                    # Later special case, add current to tbd
                    xy_cor[tbd]['tbd'] = True
                    xy_cor[tbd]['score'] -= 100
                else:
                    # Fallback: forced change the current wall or infinite loop
                    if not xy_cor[p_idx]['tbd']:
                        insert_at = tbd
                        if xy_cor[p_idx]['type'] == 0:
                            new_val = np_x_u_solve_y(xy_cor[p_idx]['val'], xy_cor[p_idx]['u1'])
                            new_type = 1
                        else:
                            new_val = np_y_u_solve_x(xy_cor[p_idx]['val'], xy_cor[p_idx]['u1'])
                            new_type = 0
                    else:
                        insert_at = n_idx
                        if xy_cor[n_idx]['type'] == 0:
                            new_val = np_x_u_solve_y(xy_cor[n_idx]['val'], xy_cor[n_idx]['u0'])
                            new_type = 1
                        else:
                            new_val = np_y_u_solve_x(xy_cor[n_idx]['val'], xy_cor[n_idx]['u0'])
                            new_type = 0
                    new_add = {'type': new_type, 'val': new_val, 'score': 0, 'action': 'forced infer', 'gpid': -1, 'u0': -1, 'u1': -1, 'tbd': False}
                    xy_cor.insert(insert_at, new_add)
            continue

        # Below checking special case
        if xy_cor[p_idx]['type'] == xy_cor[n_idx]['type']:
            #####prev and next have same type
            print('DEBUG prev and next have same type',p_idx,n_idx)
            # Two adjacency walls are same type, current wall should be differen type
            if xy_cor[tbd]['type'] == xy_cor[p_idx]['type']:
                # Fallback: three walls with same type => forced change the middle wall
                print('DEBUG three walls with same type', p_idx, tbd, n_idx)
                ####TO DO - hidden corner case - change behavior
                xy_cor[tbd]['type'] = (xy_cor[tbd]['type'] + 1) % 2
                xy_cor[tbd]['action'] = 'forced change'
                xy_cor[tbd]['val'] = xy[gpid == xy_cor[tbd]['gpid'], xy_cor[tbd]['type']].mean()
        else:
            # Two adjacency walls are different type => add one
            tp0 = xy_cor[n_idx]['type']
            tp1 = xy_cor[p_idx]['type']

            if xy_cor[p_idx]['type'] == 0:
                val0 = np_x_u_solve_y(xy_cor[p_idx]['val'], xy_cor[p_idx]['u1'])
                val1 = np_y_u_solve_x(xy_cor[n_idx]['val'], xy_cor[n_idx]['u0'])
            else:
                val0 = np_y_u_solve_x(xy_cor[p_idx]['val'], xy_cor[p_idx]['u1'])
                val1 = np_x_u_solve_y(xy_cor[n_idx]['val'], xy_cor[n_idx]['u0'])

            new_add = [
                {'type': tp0, 'val': val0, 'score': 0, 'action': 'forced infer', 'gpid': -1, 'u0': -1, 'u1': -1, 'tbd': False},
                {'type': tp1, 'val': val1, 'score': 0, 'action': 'forced infer', 'gpid': -1, 'u0': -1, 'u1': -1, 'tbd': False},
            ]                     
            
            xy_cor = xy_cor[:tbd] + new_add + xy_cor[tbd+1:]

    return xy_cor


def gen_ww(init_coorx, coory, z=50, coorW=1024, coorH=512, floorW=1024, floorH=512, tol=3, force_cuboid=True):
    ###init_coorx: 1D N equi corners ---- coory: 1024 ceiling  equi pos
        
    gpid = get_gpid(init_coorx, coorW) ####store 1D corners presence in W horizon
            
    coor = np.hstack([np.arange(coorW)[:, None], coory[:, None]])###(first dim contains 0,1,....1023 indices)
    
    ##print('gen_ww coor input', init_coorx.shape, coory.shape)

    ####transform equi uv to cartesian xy - 1024x2 
    xy = np_coor2xy(coor, z, coorW, coorH, floorW, floorH)

    ##print('gen_ww xy', xy.shape)
       
    # Generate wall-wall
    if force_cuboid:
        xy_cor = gen_ww_cuboid(xy, gpid, tol)
    else:
        xy_cor = gen_ww_general(init_coorx, xy, gpid, tol)####input: N corners as equi horizontal pos, 1024x2 XY coords of the ceiling boundary

    ##print(xy_cor.shape)
    
    # Ceiling view to normal view
    cor = []
    for j in range(len(xy_cor)):
        next_j = (j + 1) % len(xy_cor)
        if xy_cor[j]['type'] == 1:
            cor.append((xy_cor[next_j]['val'], xy_cor[j]['val']))
        else:
            cor.append((xy_cor[j]['val'], xy_cor[next_j]['val']))

    cor = np_xy2coor(np.array(cor), z, coorW, coorH, floorW, floorH)
    cor = np.roll(cor, -2 * cor[::2, 0].argmin(), axis=0)
        
    
    return cor, xy_cor

### MINE generate transform footprint
def equi_to_xy_contour(equi_coor, z0, z1, coorW=1024, coorH=512, floorW=1024 , floorH=1024, c_scaling = 1.0, f_scaling = 1.0):
     ####
     ceiling_edge = equi_coor[0]
     floor_edge = equi_coor[1]
          
     ####stacking to 1024x2
     c_coor = np.hstack([np.arange(coorW)[:, None], ceiling_edge[:, None]])
     f_coor = np.hstack([np.arange(coorW)[:, None], floor_edge[:, None]])
              
    ####transform equi uv to cartesian xy
     c_xy = np_coor2xy(c_coor, z0, coorW, coorH, floorW, floorH, c_scaling)
     f_xy = np_coor2xy(f_coor, z1, coorW, coorH, floorW, floorH, f_scaling)

     print('xy shape',c_xy.shape)
              
     return c_xy, f_xy

def get_drawable_contour(c_xy, f_xy, floorW=1024 , floorH=1024):
     c_footprint = np.zeros((floorW, floorH, 3), np.uint8)
     f_footprint = np.zeros((floorW, floorH, 3), np.uint8)

     c_pts = c_xy.astype(np.int32)
     f_pts = f_xy.astype(np.int32)         
                        
     c_pts = c_pts.reshape((-1,1,2))
     f_pts = f_pts.reshape((-1,1,2))
                         
     cv2.polylines(c_footprint, [c_pts], True, (0,0,255),2,cv2.LINE_AA)
     cv2.polylines(f_footprint, [f_pts], True, (255,0,0),2,cv2.LINE_AA)

     return c_footprint,f_footprint

def draw_overlay_footprint(c_f, f_f, c_xy, f_xy):

     c_footprint = c_f.copy()
     f_footprint = f_f.copy()
         
               
     c_pts = c_xy.astype(np.int32)
     f_pts = f_xy.astype(np.int32)         
                        
     c_pts = c_pts.reshape((-1,1,2))
     f_pts = f_pts.reshape((-1,1,2))
                         
     cv2.polylines(c_footprint, [c_pts], True, (0,0,255),2,cv2.LINE_AA)
     cv2.polylines(f_footprint, [f_pts], True, (255,0,0),2,cv2.LINE_AA)
         
     return c_footprint,f_footprint



