import bpy
import math

def pipeline_split_and_sort_v8():
    # --- CONFIGURATION ---
    
    COL_SPLIT_NAME = "Process_SPLIT_ME" 
    
    # SIZE THRESHOLDS
    SIZE_SMALL_MAX = 1.1    
    SIZE_DOOR_MAX  = 3.0    
    SIZE_MED_MAX   = 20.0   
    
    # VIP VERTEX COUNTS (For Identity Check)
    DOOR_VIP_COUNTS = [7, 8, 11, 14, 16, 17, 18, 26] 
    
    # STRICT CURVATURE
    USE_STRICT_CURVE = True
    RATIO_THRESHOLD = 1.01

    # --- KEYWORD LISTS (Case Insensitive) ---
    # 1. DOORS
    KEYS_DOOR = ["DOOR", "SWING", "SINGLE", "DOUBLE", "UNBALANCED", "ENTRANCE"]
    
    # 2. SANITARY (Bathrooms)
    KEYS_SANITARY = ["TOILET", "SINK", "URINAL", "WC", "LAVATORY", "BATH"]
    
    # 3. FURNITURE (Chairs/Seating)
    KEYS_CHAIRS = ["CHAIR", "LOUNGE", "SEAT", "SOFA", "BENCH", "STOOL"]
    
    # 4. STRUCTURE (Optional - usually finding by size is safer for walls)
    KEYS_WALL = ["WALL", "EXTERIOR", "GLAZING", "CURTAIN"]

    # --- SETUP COLLECTIONS ---
    def get_collection(name, color=None):
        if name in bpy.data.collections:
            col = bpy.data.collections[name]
        else:
            col = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(col)
        if color: col.color_tag = color
        return col

    # Colors: 01=Red, 02=Orange, 03=Yellow, 04=Green, 05=Blue, 06=Purple, 07=Pink, 08=Brown
    c_split = get_collection(COL_SPLIT_NAME, 'COLOR_01')     # Red Hopper
    
    c_doors = get_collection("SORT_Doors_Clean", 'COLOR_04') # Green
    c_check = get_collection("SORT_Doors_Manual_Check", 'COLOR_02') # Orange
    
    c_chairs = get_collection("SORT_Furniture_Chairs", 'COLOR_05') # Blue
    c_sanit  = get_collection("SORT_Room_Sanitary", 'COLOR_06') # Purple
    
    c_small = get_collection("SORT_Small_Details", 'COLOR_08') # Brown/Grey
    c_med   = get_collection("SORT_Medium_Objects")            # Default
    c_large = get_collection("SORT_Large_Structure")           # Default

    # --- HELPER: CURVATURE ---
    def is_curved(obj):
        try:
            total_len = 0.0
            points_count = 0
            if obj.type == 'CURVE':
                for spline in obj.data.splines:
                    points_count += len(spline.points) + len(spline.bezier_points)
                    if len(spline.points) > 0:
                        pts = spline.points
                        for i in range(len(pts)-1):
                            total_len += (pts[i].co.to_3d() - pts[i+1].co.to_3d()).length
                    elif len(spline.bezier_points) > 0:
                        pts = spline.bezier_points
                        for i in range(len(pts)-1):
                            total_len += (pts[i].co - pts[i+1].co).length
            elif obj.type == 'MESH':
                 return True # Skip strict check for meshes
            
            dims = obj.dimensions
            diag = math.sqrt(dims.x**2 + dims.y**2)
            if diag < 0.001 or points_count < 3: return False
            return (total_len / diag) > RATIO_THRESHOLD
        except:
            return False

    # --- PHASE 1: SPLITTER (Red Hopper) ---
    print(f"--- PHASE 1: RED HOPPER ---")
    objects_to_split = [obj for obj in c_split.objects if obj.type in ['MESH', 'CURVE']]
    if objects_to_split:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects_to_split:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target='MESH')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.005) 
            bpy.ops.mesh.separate(type='LOOSE') 
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.convert(target='CURVE')
            obj.select_set(False)

    # --- PHASE 2: SORTING ---
    print("--- PHASE 2: TAXONOMY SORT ---")
    targets = [obj for obj in bpy.context.scene.objects if obj.type in ['MESH', 'CURVE'] and obj.visible_get()]
    
    # Counters
    cnt = {k:0 for k in ['door', 'check', 'chair', 'sanit', 'small', 'med', 'large']}

    for obj in targets:
        dims = obj.dimensions
        max_dim = max(dims.x, dims.y, dims.z)
        name_upper = obj.name.upper()
        
        # Count Points
        p_count = 0
        if obj.type == 'CURVE':
            for spline in obj.data.splines:
                p_count += len(spline.points) + len(spline.bezier_points)
        elif obj.type == 'MESH':
            p_count = len(obj.data.vertices)

        target_col = None

        # --- LOGIC TREE ---
        
        # 1. NAME FILTERS (Taxonomy)
        if any(k in name_upper for k in KEYS_DOOR):
            # Safety: Don't put giant walls or tiny screws in Doors just because they are named "Single"
            if 0.5 < max_dim < 4.0:
                target_col = c_doors
                cnt['door'] += 1
            else:
                target_col = c_check # Name matched, but size was weird -> Check it
                cnt['check'] += 1
                
        elif any(k in name_upper for k in KEYS_CHAIRS):
            target_col = c_chairs
            cnt['chair'] += 1
            
        elif any(k in name_upper for k in KEYS_SANITARY):
            target_col = c_sanit
            cnt['sanit'] += 1
            
        # 2. VIP CHECK (Identity + Curvature)
        # If it wasn't named properly, we check the geometry fingerprint
        elif p_count in DOOR_VIP_COUNTS:
            if USE_STRICT_CURVE:
                if is_curved(obj):
                    target_col = c_doors
                    cnt['door'] += 1
                else:
                    target_col = c_check
                    cnt['check'] += 1
            else:
                target_col = c_doors
                cnt['door'] += 1
            
        # 3. SIZE SORTING (The Rest)
        elif max_dim < SIZE_SMALL_MAX:
            target_col = c_small
            cnt['small'] += 1
            
        elif max_dim < SIZE_DOOR_MAX:
            target_col = c_check # Potential unnamed doors
            cnt['check'] += 1
        
        elif max_dim < SIZE_MED_MAX:
            target_col = c_med
            cnt['med'] += 1
            
        else:
            target_col = c_large
            cnt['large'] += 1

        # MOVE
        if target_col:
            current_cols = obj.users_collection
            if target_col not in current_cols:
                for old_col in current_cols:
                    old_col.objects.unlink(obj)
                target_col.objects.link(obj)

    print(f"TAXONOMY COMPLETE.")
    print(f"Doors (Clean):   {cnt['door']}")
    print(f"Chairs:          {cnt['chair']}")
    print(f"Sanitary:        {cnt['sanit']}")
    print(f"Check/Unknown:   {cnt['check']}")
    print(f"Medium Objects:  {cnt['med']}")
    print("-" * 30)

pipeline_split_and_sort_v8()