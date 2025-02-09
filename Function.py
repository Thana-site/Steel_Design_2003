# Import libraries
import streamlit as st #version 1.42.0
import pandas as pd #version 2.2.2.
import matplotlib.pyplot as plt  # Correct import for matplotlib
import matplotlib.patches as patches #version 3.9.2.
import math as mt 
import numpy as np #version 2.1.0
import altair as alt #version 5.4.1.
import plotly.express as px #6.0.0
from st_aggrid import AgGrid,GridOptionsBuilder #version 1.1.0
import os 

# File paths
file_path = r"C:\Users\Lenovo\OneDrive\Project to the moon\2003_APP\2003-Steel Design\2003-Steel-Beam\Steel_Design_2003\2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = r"C:\Users\Lenovo\OneDrive\Project to the moon\2003_APP\2003-Steel Design\2003-Steel-Beam\Steel_Design_2003\2003-Steel-Beam-DataBase-Material.csv"

# Check if the files exist before loading them
if os.path.exists(file_path) and os.path.exists(file_path_mat):
    try:
        # Read the CSV files
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding='ISO-8859-1')

        # Print columns to verify
        print("Columns in df:", df.columns)
        print("Columns in df_mat:", df_mat.columns)

        # Generate section list based on whether "Section" is a column or index
        if "Section" in df.columns:
            section_list = df["Section"].tolist()
        else:
            section_list = df.index.tolist()  # Use the index if "Section" is not found

        # Generate section list based on whether "Grade" is a column or index
        if "Grade" in df_mat.columns:
            section_list_mat = df_mat["Grade"].tolist()
        else:
            section_list_mat = df_mat.index.tolist()  # Use the index if "Grade" is not found
        
        # Print the results
        print("Files loaded successfully!")
        print("Section list:", section_list)
        print("Material section list:", section_list_mat)

    except Exception as e:
        print(f"An error occurred while loading the files: {e}")
else:
    print("One or both files do not exist at the given paths. Please check the file paths.")

# Streamlit Interface
st.subheader("Structural Steel Design", divider="red")

# Default selected options
option = "W-100x50x5x7 (9.3 kg/m)"  # Initial default value for section
option_mat = 'SS400'  # Initial default value for material
bending_axis = "Major axis bending"

# Toggle for enabling Chapter F Strength input
ChapterF_Strength = st.sidebar.checkbox("For Chapter F Strength")

if ChapterF_Strength:
    # Dropdown to select a section
    option = st.sidebar.selectbox("Choose a Steel Section:", section_list, index=section_list.index(option) if option in section_list else 0)

    # Dropdown to select a material grade
    option_mat = st.sidebar.selectbox("Choose a Steel Grade:", section_list_mat, index=section_list_mat.index(option_mat) if option_mat in section_list_mat else 0)

    # Dropdown to select a bending axis
    bending_axis = st.sidebar.selectbox(
        "Select Bending Axis:",  # More appropriate label
        ("Major axis bending", "Minor axis bending"),
        index=None,  # No default selection
        placeholder="Select bending axis..."  # Relevant placeholder text
    )


Mu = 100
Vu = 100

# Toggle for enabling Chapter F Design input
ChapterF_Design = st.sidebar.checkbox("For Chapter F Design")
if ChapterF_Design:
    # Input for Ultimate Bending Moment
    Mu = st.sidebar.number_input("Input Ultimate Bending Moment:")

    # Input for Ultimate Shear Force
    Vu = st.sidebar.number_input("Input Ultimate Shear Force:")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Structural Steel Catalogue", "Chapter F (Strength)", "Steel Catalogue", "Chapter F (Design)"])

with tab1:
    cols = st.columns(3)
    with cols[0]:
        # Debug: Check if option is defined and valid
        if option:
            if option in df.index:
                st.write(f"Details for **{option}**:")
                st.write(df.loc[option])
            else:
                st.warning("Selected section not found in the database!")
        else:
            st.warning("No section selected.")

        # Display details for the selected material section
        st.write(f"Details for **{option_mat}**:")

        if option_mat in df_mat.index:
            st.write(df_mat.loc[option_mat])
        else:
            st.warning("Selected section not found in the database!")

    with cols[1]:
        # Assuming the necessary dataframe (df) and option are defined elsewhere in the code
        st.write("Section Show:")

        # Extract values from the dataframe for the selected section and convert them to float
        if option in df.index:
            bf = float(df.loc[option, 'bf [mm]'])  # flange width [mm]
            d = float(df.loc[option, 'd [mm]'])    # depth [mm]
            tw = float(df.loc[option, 'tw [mm]'])   # web thickness [mm]
            tf = float(df.loc[option, 'tf [mm]'])   # flange thickness [mm]
            r = float(df.loc[option, 'r [mm]'])    # corner radius [mm]
            # Calculate the centroid (y-centroid is calculated as halfway from the top to the web's top edge)
            y_centroid = (d - tf) / 2  # For the y-centroid, it's halfway from the top to the web's top edge

            # Create figure and axis with dark mode background
            fig, ax = plt.subplots()

            # Set the background color to dark
            fig.patch.set_facecolor('black')  # Set figure background to black
            ax.set_facecolor('black')         # Set axis background to black
            ax.tick_params(axis='x', colors='white')  # Set x-axis ticks to white
            ax.tick_params(axis='y', colors='white')  # Set y-axis ticks to white

            # Create H-shape with flange and web
            flange_top = patches.Rectangle((-bf/2, d/2 - tf), bf, tf, linewidth=1, edgecolor='b', facecolor='lightblue')
            flange_bottom = patches.Rectangle((-bf/2, -d/2), bf, tf, linewidth=1, edgecolor='b', facecolor='lightblue')
            web = patches.Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf, linewidth=1, edgecolor='b', facecolor='lightblue')

            # Add patches to the plot
            ax.add_patch(flange_top)
            ax.add_patch(flange_bottom)
            ax.add_patch(web)

            # Add centroid axis (horizontal centroid axis is at y = 0, and vertical at x = 0)
            ax.axhline(y=0, color='red', linewidth=1, linestyle='--')  # Horizontal centroid axis (y = 0)
            ax.axvline(x=0, color='red', linewidth=1, linestyle='--')  # Vertical centroid axis (x = 0)

            # Set limits and aspect ratio
            ax.set_xlim([-bf/2 - 20, bf/2 + 20])
            ax.set_ylim([-d/2 - 20, d/2 + 20])
            ax.set_aspect('equal')

            # Set labels and title with light-colored text
            ax.set_title("H-Shape Steel Section with Centroid Axes", color='white')
            ax.set_xlabel("Width [mm]", color='white')
            ax.set_ylabel("Height [mm]", color='white')

            # Set grid with light-colored grid lines
            ax.grid(True, color='white')

            # Display the plot using Streamlit's pyplot function
            st.pyplot(fig)  # Display in Streamlit
        else:
            st.warning("Please select a valid section!")
        
        # (Flexural) Table 4.1b : Compression Elements Member Subject to Flexure
        def Flexural_classify(df, df_mat, option, option_mat):
            #call the data subjected to grade of Structural Steel
            Fy = float(df_mat.loc[option_mat,"Yield Point (ksc)"])
            E = float(df_mat.loc[option_mat,"E"])

            # Convert DataFrame values to float
            lamw = float(df.loc[option, 'h/tw'])
            lamf = float(df.loc[option, '0.5bf/tf'])
            
            lamw_limp = 3.76 * mt.sqrt(E / Fy)
            lamw_limr = 5.70 * mt.sqrt(E / Fy)

            lamf_limp = 0.38 * mt.sqrt(E / Fy)
            lamf_limr = 1.00 * mt.sqrt(E / Fy)

            # Classify based on limiting values
            if lamw < lamw_limp:
                Classify_Web_Flexural = "Compact Web"
            elif lamw_limp < lamw < lamw_limr:
                Classify_Web_Flexural = "Non-Compact Web"
            else:
                Classify_Web_Flexural = "Slender Web"
                
            if lamf < lamf_limp:
                Classify_flange_Flexural = "Compact Flange"
            elif lamf_limp < lamf < lamf_limr:
                Classify_flange_Flexural = "Non-Compact Flange"
            else:
                Classify_flange_Flexural = "Slender Flange"

            # Return all relevant values
            return lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural

        # Call the function and capture the returned values
        lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_flexural, Classify_Web_flexural = Flexural_classify(df, df_mat, option, option_mat)

        # (Compression) Table 4.1a : Compression Elements Member Subject to Axial Compression
        def compression_classify(df, df_mat, option, option_mat):
            # Convert DataFrame values to float
            Fy = float(df_mat.loc[option_mat,"Yield Point (ksc)"])
            E = float(df_mat.loc[option_mat,"E"])          
            lamw = float(df.loc[option, 'h/tw'])
            lamf = float(df.loc[option, '0.5bf/tf'])
            lamw_lim = 1.49 * mt.sqrt(E / Fy)
            lamf_lim = 0.56 * mt.sqrt(E / Fy)
            
            # Classify based on limiting values
            if lamw < lamw_lim:
                Classify_Web_Compression = "Non-Slender Web"
            else:
                Classify_Web_Compression = "Slender Web"
                
            if lamf < lamf_lim:
                Classify_flange_Compression = "Non-Slender Flange"
            else:
                Classify_flange_Compression = "Slender Flange"
                
            return lamf, lamw, lamw_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression

        # Call the function and capture the returned values
        lamf, lamw, lamw_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression = compression_classify(df, df_mat, option, option_mat)

        # Organize classification results into a vertical DataFrame
        def create_vertical_classification_dataframe(option, 
                                                    Classify_flange_Compression, Classify_Web_Compression, 
                                                    Classify_flange_Flexural, Classify_Web_Flexural):
            # Create a list of tuples to store classification data in a vertical format
            data = [
                ("Section", option),
                ("Flange_Compression:", Classify_flange_Compression),
                ("Web_Compression:", Classify_Web_Compression),
                ("Flange_Flexural:", Classify_flange_Flexural),
                ("Web_Flexural:", Classify_Web_Flexural)
            ]
            # Convert the list of tuples to a pandas DataFrame
            return pd.DataFrame(data, columns=["Property", "Value"])

        # Call the classification functions
        lamf, lamw, lamw_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression = compression_classify(df, df_mat, option, option_mat)
        lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural = Flexural_classify(df, df_mat, option, option_mat)

        # Create a vertical DataFrame with classification results
        vertical_classification_df = create_vertical_classification_dataframe(
            option, 
            Classify_flange_Compression, Classify_Web_Compression, 
            Classify_flange_Flexural, Classify_Web_Flexural
        )

        # Display the vertical DataFrame in Streamlit
        st.write("Classification Results (Vertical Format):")
        st.dataframe(vertical_classification_df)

    with cols[2]:
        st.dataframe(df, height=00)

    
with tab2:
    st.subheader("Flexural Design (According to Chapter F)", divider="green")

with tab2:
    # F2: DOUBLY SYMMETRIC COMPACT I-SHAPED MEMBERS AND CHANNELS BENT ABOUT THEIR MAJOR AXIS
    def F2(df, df_mat, option, option_mat,Lb):
        Cb = 1
        section = option
        Lb = Lb * 100  # Convert Lb to cm
        Lp = float(df.loc[section, "Lp [cm]"])
        Lr = float(df.loc[section, "Lr [cm]"])
        S_Major = float(df.loc[section, "Sx [cm3]"])
        Z_Major = float(df.loc[section, 'Zx [cm3]'])
        rts = float(df.loc[section, 'rts [cm6]'])
        j = float(df.loc[section, 'j [cm4]'])
        c = 1
        h0 = float(df.loc[section, 'ho [mm]']) / 10  # Convert to cm
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        E = float(df_mat.loc[option_mat, "E"])

        Mni = []
        Mnr = []
        Lni = []
        Lri_values = []

        if Lb < Lp:
            Case = "F2.1"
            Mp = Fy * Z_Major 
            Mn = Mp/100000
            Mn = np.floor(Mn * 100) / 100
            Mp = np.floor(Mp * 100) / 100
        elif Lp <= Lb < Lr:
            Case = "F2B"
            Mp = Fy * Z_Major
            Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb - Lp) / (Lr - Lp))))
            Mn = Mn / 100000
            Mp = Mp/100000
            Mn = min(Mp,Mn)
            Mn = np.floor(Mn * 100) / 100
            Mp = np.floor(Mp * 100) / 100
        else:
            Case = "F2C"
            Term_1 = (Cb * mt.pi ** 2 * E) / (((Lb) / rts) ** 2)
            Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * (((Lb) / rts) ** 2)
            Term12 = Term_1 * mt.sqrt(1 + Term_2)
            Mn = Term12*S_Major
            Mn = Mn/100000
            Mp = Fy * Z_Major 
            Mp = Mp/100000
            Mn = np.floor(Mn * 100) / 100
            Mp = np.floor(Mp * 100) / 100

        Mn = np.floor(Mn * 100) / 100
        Mn_F2C = 0.7 * Fy * S_Major / 100000
        Mn_F2C = np.floor(Mn_F2C * 100) / 100

        Mni.append(Mp)
        Lni.append(np.floor(0 * 100) / 100)

        Mni.append(Mp)
        Lni.append(np.floor((Lp/100) * 100) / 100)

        Mni.append(Mn_F2C)
        Lni.append(np.floor((Lr/100) * 100) / 100)

        # Adjust Lr rounding logic
        Lro = Lr
        Lr = Lr / 100  # Convert to meters for calculation
        Lr = np.ceil(Lr * 100) / 100  # Round up to the second decimal place
        Lr += 0.01  # Add 0.1
        Lrii = Lr  # Start of the range
        Lriii = Lrii + 11  # Add 10 to the range

        # Modify the loop with step size of 0.5
        i = Lrii
        while i < Lriii:
            Lbi = i * 100  # Convert to cm
            rounded_i = np.floor(i * 100) / 100  # Ensure i is rounded to two decimals
            Lri_values.append(rounded_i)
            
            # Calculate Mn using Term_1 and Term_2
            Term_1 = (Cb * mt.pi ** 2 * E) / ((Lbi / rts) ** 2)
            Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * ((Lbi / rts) ** 2)
            fcr = Term_1 * mt.sqrt(1 + Term_2)
            Mnc = fcr*S_Major
            Mnc = Mnc / 100000  # Convert to kNm
            Mnc = np.floor(Mnc * 100) / 100  # Round to two decimal places
            Mnr.append(Mnc)
            
            i += 0.5  # Increment by 0.5

        # Append results after the loop
        Mni.append(Mnr)
        Lni.append(Lri_values)

        Lb = Lb/100
        Lp = Lp/100
        Lr = Lro/100

        Lb = np.floor(Lb * 100) / 100
        Lp = np.floor(Lp * 100) / 100
        Lr = np.floor(Lr * 100) / 100

        return Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case

    # F3: Doubly Symmetric I-Shaped Members with Compact Webs and Noncompact or Slender Flanges Bent about Their Major Axis
    def F3(df, df_mat, option, option_mat, lamf, lamf_limp, lamf_limr, Classify_flange_Flexural, Classify_Web_Flexural):
        Cb = 1
        section = option
        Lb = 6 * 100  # Convert Lb to cm
        Lp = float(df.loc[section, "Lp [cm]"])
        Lr = float(df.loc[section, "Lr [cm]"])
        S_Major = float(df.loc[section, "Sx [cm3]"])
        Z_Major = float(df.loc[section, "Zx [cm3]"])
        rts = float(df.loc[section, "rts [cm6]"])
        j = float(df.loc[section, "j [cm4]"])
        tf = float(df.loc[section, "tf [mm]"])
        tw = float(df.loc[section, "tw [mm]"])
        r = float(df.loc[section, "r [mm]"])
        d = float(df.loc[section, "d [mm]"])
        h = d - 2 * (tf + r)  # mm.
        c = 1
        h0 = float(df.loc[section, "ho [mm]"]) / 10  # Convert to cm
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        E = float(df_mat.loc[option_mat, "E"])
        Mp = Fy * Z_Major / 100000
        Mp = np.floor(Mp * 100) / 100

        Mni = []
        lam = []
        lamf_limr_values = []
        Mnr = []

        # F3.1 (LTB), Same as the provisions F2.2
        if Lb < Lp:
            Case = "plastic yielding"
            Mn = Mp
        elif Lp <= Lb < Lr:
            Case = "F3.1B"
            Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb - Lp) / (Lr - Lp))))
            Mn = Mn / 100000
        else:
            Case = "F3.2C"
            Term_1 = (Cb * mt.pi**2 * E) / ((Lb / rts)**2)
            Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * ((Lb / rts)**2)
            Mn = Term_1 * mt.sqrt(1 + Term_2)
            Mn = Mn / 100000

        # F3.2 (Compression Flange Local Buckling)
        if Classify_Web_Flexural == "Compact Web" and Classify_flange_Flexural == "Non-Compact Flange":
            Mn = Mp - ((Mp - (0.7 * Fy * S_Major / 100000)) * ((lamf - lamf_limp) / (lamf_limr - lamf_limp)))
        elif Classify_Web_Flexural == "Compact Web" and Classify_flange_Flexural == "Slender Flange":
            Kc = 4 / np.sqrt(h / tw)
            if Kc < 0.35:
                Kc = 0.35
            elif Kc > 0.76:
                Kc = 0.76
            Mn = (0.9 * E * Kc * S_Major) / (lamf**2)
            Mn = Mn / 100000

        # Define Mn in 2 decimal places
        Mn = np.floor(Mn * 100) / 100

        # Prepare data in lists
        Mn_r = 0.7 * Fy * S_Major / 100000
        Mn_r = np.floor(Mn_r * 100) / 100

        Mni.append(Mp)
        lam.append(np.floor(0 * 100) / 100)

        Mni.append(Mp)
        lam.append(np.floor(lamf_limp * 100) / 100)

        Mni.append(Mn_r)
        lam.append(np.floor(lamf_limr * 100) / 100)

        # Adjust Lr rounding logic
        lamf_limr = np.ceil(lamf_limr * 100) / 100  # Round up to the second decimal place
        lamf_limr += 0.5  # Add 0.1
        lamf_limrii = lamf_limr  # Start of the range
        lamf_limriii = lamf_limrii + 10  # Add 10 to the range

        i = lamf_limrii
        while i < lamf_limriii:
            rounded_i = np.floor(i * 100) / 100  # Ensure i is rounded to two decimals
            lamf_limr_values.append(rounded_i)
            # Calculate Mn using Term_1 and Term_2
            Kc = 4 / mt.sqrt(h / tw)
            if Kc < 0.35:
                Kc = 0.35
            elif Kc > 0.76:
                Kc = 0.76
            Mnc = (0.9 * E * Kc * S_Major) / (i**2)
            Mnc = Mnc / 100000
            Mnc = np.floor(Mnc * 100) / 100  # Round to two decimal places
            Mnr.append(Mnc)
            
            i += 1  # Increment by 0.5

        # Append results after the loop
        Mni.append(Mnr)
        lam.append(lamf_limr_values)   
        
        return Mn, Lb, Lp, Lr, Mp, Mni, lam
    
    def F6(df, df_mat, option, option_mat, lamf, lamf_limp, lamf_limr, Classify_flange_Flexural, Classify_Web_Flexural):
        Cb = 1
        section = option
        Lb = 6 * 100  # Convert Lb to cm
        Lp = float(df.loc[section, "Lp [cm]"])
        Lr = float(df.loc[section, "Lr [cm]"])
        S_Minor = float(df.loc[section, "Sy [cm3]"])
        Z_Minor = float(df.loc[section, "Zy [cm3]"])
        rts = float(df.loc[section, "rts [cm6]"])
        j = float(df.loc[section, "j [cm4]"])
        tf = float(df.loc[section, "tf [mm]"])
        bf = float(df.loc[section, "bf [mm]"])
        tw = float(df.loc[section, "tw [mm]"])
        r = float(df.loc[section, "r [mm]"])
        d = float(df.loc[section, "d [mm]"])
        h = d - 2 * (tf + r)  # mm.
        c = 1
        h0 = float(df.loc[section, "ho [mm]"]) / 10  # Convert to cm
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        E = float(df_mat.loc[option_mat, "E"])

        Mni = []
        lam = []
        lamf_limr_values = []
        Mnr = []
        
        # F6.1: Plastic Yielding
        Mp1 = Fy * Z_Minor
        Mp2 = 1.6 * Fy * S_Minor
        if Mp1 < Mp2:
            Mp = Mp1 / 100000
        else:
            Mp = Mp2 / 100000
        Mp = np.floor(Mp * 100) / 100  # Round down to 2 decimal places
        
        # F6.2: Flange Local Buckling
        if Classify_flange_Flexural == "Compact Flange":
            Mn = Mp
            case = "Compact Flange"
        elif Classify_flange_Flexural == "Non-Compact Flange":
            Mn = Mp - ((Mp - (0.7 * Fy * S_Minor / 100000)) * ((lamf - lamf_limp) / (lamf_limr - lamf_limp)))
            case = "Non-Compact Flange"
        else:  # Slender Flange
            Fcr = (0.69 * E) / ((0.5 * bf) / tf) ** 2
            Mn = Fcr * S_Minor / 100000
            case = "Slender Flange"
        Mn = np.floor(Mn * 100) / 100  # Round down to 2 decimal places

        # Prepare data in lists
        Mn_r = 0.7 * Fy * S_Minor / 100000
        Mn_r = np.floor(Mn_r * 100) / 100

        Mni.append(Mp)
        lam.append(np.floor(0 * 100) / 100)

        Mni.append(Mp)
        lam.append(np.floor(lamf_limp * 100) / 100)

        Mni.append(Mn_r)
        lam.append(np.floor(lamf_limr * 100) / 100)
        
        return Mn, Mp, Mni, lam, case
    
    flange = Classify_flange_flexural
    web = Classify_Web_flexural   
    
    def classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis):
        # Classify flange compactness based on limiting values
        if lamf < lamf_limp:
            flange = "Compact Flange"
        elif lamf_limp <= lamf < lamf_limr:
            flange = "Non-Compact Flange"
        else:
            flange = "Slender Flange"
        
        # Classify web compactness based on limiting values
        if lamw < lamw_limp:
            web = "Compact Web"
        elif lamw_limp <= lamw < lamw_limr:
            web = "Non-Compact Web"
        else:
            web = "Slender Web"
        
        # Check for major axis bending
        if bending_axis == "Major axis bending":
            if flange == "Compact Flange" and web == "Compact Web":
                return "F2: Doubly Symmetric Compact I-Shaped Members Bent about Major Axis"
            elif flange == "Non-Compact Flange" and web == "Compact Web":
                return "F3(NC-C): I-Shaped Members with Noncompact Flange, Compact Web Bent about Major Axis"
            elif flange == "Slender Flange" and web == "Compact Web":
                return "F3(S-C): I-Shaped Members with Slender Flange, Compact Web Bent about Major Axis"
            elif flange == "Compact Flange" and web == "Non-Compact Web":
                return "F4(C-NC): I-Shaped Members with Compact Flange, Noncompact Web Bent about Major Axis"
            elif flange == "Non-Compact Flange" and web == "Non-Compact Web":
                return "F4(NC-NC): I-Shaped Members with Noncompact Flange, Noncompact Web Bent about Major Axis"
            elif flange == "Slender Flange" and web == "Non-Compact Web":
                return "F4(S-NC): I-Shaped Members with Slender Flange, Noncompact Web Bent about Major Axis"
            elif flange == "Compact Flange" and web == "Slender Web":
                return "F5(C-S): I-Shaped Members with Compact Flange, Slender Web Bent about Major Axis"
            elif flange == "Non-Compact Flange" and web == "Slender Web":
                return "F5(NC-S): I-Shaped Members with Noncompact Flange, Slender Web Bent about Major Axis"
            elif flange == "Slender Flange" and web == "Slender Web":
                return "F5(S-S): I-Shaped Members with Slender Flange, Slender Web Bent about Major Axis"
        
        # Check for minor axis bending
        elif bending_axis == "Minor axis bending":
            if flange == "Compact Flange":
                return "F6(C-All): I-Shaped Members Bent about Minor Axis (Compact Flange)"
            elif flange == "Non-Compact Flange":
                return "F6(NC-All): I-Shaped Members Bent about Minor Axis (Noncompact Flange)"
            elif flange == "Slender Flange":
                return "F6(S-All): I-Shaped Members Bent about Minor Axis (Slender Flange)"
        
        return "Error: Classification not found."

    result = classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis)
    st.write("You selected:",result)
    # Create columns for two input modes
    left, right = st.columns(2)

    # Use session state to track input method
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "slider"

    # Buttons to switch between input modes
    if left.button("Slider Number", use_container_width=True):
        st.session_state.input_mode = "slider"
    if right.button("Number Input", use_container_width=True):
        st.session_state.input_mode = "number"
    

    Lr = df.loc[option, 'Lr [cm]']/100
    Lr = mt.ceil(Lr)

    # Display the appropriate input widget
    if st.session_state.input_mode == "slider":
        Lb = st.slider("Input Unbraced Length (Lb).", 0, Lr+10)
    else:
        Lb = st.number_input("Input Unbraced Length (Lb).")

    st.write("The current number is:", Lb)


    # Adjust column widths: col_F[1] takes 3 parts, col_F[0] takes 1 part
    col_F = st.columns([2, 4])  

    if result == "F2: Doubly Symmetric Compact I-Shaped Members Bent about Major Axis":
        with col_F[0]:
            try:
                # Call the function with mocked inputs
                Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, option, option_mat, Lb)
                
                Fib = 0.9
                FibMn = 0.9 * Mn

                # Create DataFrame for results
                result_data = {
                    "Parameter": ["Mn (t-m.)", "Lb (m.)", "Lp (m.)", "Lr (m.)", "Mp (t-m.)", "Case", "Fib", "FibMp (t-m.)"],
                    "Value": [Mn, Lb, Lp, Lr, Mp, Case, Fib, FibMn]
                }

                result_df = pd.DataFrame(result_data)
                
                # Display the results in a DataFrame
                st.write(option)
                st.dataframe(result_df)

            except Exception as e:
                st.error(f"Error in calculation: {e}")

        with col_F[1]:
            try:
                # Flatten the nested lists for plotting
                Mni_flat = Mni[:3] + Mni[3]
                Lni_flat = Lni[:3] + Lni[3]

                # Initialize flat lists
                Lb_flat = []
                Mn_flat = []

                # Create lists for Lb_flat and Mn_flat
                for i in range(len(Mni_flat)):
                    Lb_flat.append(Lb)  # Assuming Lb is a constant
                    Mn_flat.append(Mn)  # Assuming Mn is a constant

                # Convert data to a pandas DataFrame for plotting
                data = pd.DataFrame({
                    "Lni (Length, m)": Lni_flat,
                    "Lb (Length, m)": Lb_flat,
                    "Mni (Moment, t-m)": Mni_flat,
                    "Mn (Moment t-m)": Mn_flat,
                })

                # Plot the graph using Plotly Express
                fig = px.line(data, x="Lni (Length, m)", y=["Mni (Moment, t-m)", "Mn (Moment t-m)"],
                            title="Nominal Moment (Mn) vs. Unbraced Length (Lb)",
                            labels={"Lni (Length, m)": "Length (m)",
                                    "Mni (Moment, t-m)": "Moment (t-m)",
                                    "Mn (Moment t-m)": "Moment (t-m)"})

                # Add vertical line for Lb (constant)
                fig.add_vline(x=Lb, line=dict(color="red", dash="dot"), 
                            annotation_text="Lb", annotation_position="top")

                # Add axis titles using update_layout
                fig.update_layout(
                    xaxis_title="Unbraced Length (Lb)",  # Title for the x-axis
                    yaxis_title="Nominal Moment (Mn)",  # Title for the y-axis
                )

                st.plotly_chart(fig)

            except Exception as e:
                st.error(f"Error in plotting: {e}")

    elif result == "F6(C-All): I-Shaped Members Bent about Minor Axis (Compact Flange)":
        with col_F[0]:
            try:
                # Call the function with required inputs
                Mn, Mp, Mni, lam, case = F6(df, df_mat, option, option_mat, lamf, lamf_limp, lamf_limr, Classify_flange_Flexural, Classify_Web_Flexural)
                lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_flexural, Classify_Web_flexural = Flexural_classify(df, df_mat, option, option_mat)

                Fib = 0.9
                FibMn = Fib*Mn

                # Create a DataFrame to display results
                result_data = {
                    "Parameter": ["Mn (t-m.)", "Mp (t-m.)", "Mni (t-m.)", "λ flange", "λ flange (p)", "λ flange (r)", "Case", "FibMn (t-m.)"],
                    "Value": [Mn, Mp, Mni, lamf, lamf_limp, lamf_limr, case, FibMn]
                }
                result_df = pd.DataFrame(result_data)

                # Display results
                st.write(option)
                st.dataframe(result_df)

            except Exception as e:
                st.error(f"Error in calculation: {e}")

        with col_F[1]:
            try:
                # Ensure list length before indexing
                Mni_flat = Mni[:3]  # Take first three values
                lami_flat = lam[:3]  # Take first three values

                # Add fourth element only if available
                if len(Mni) > 3:
                    Mni_flat += Mni[3] if isinstance(Mni[3], list) else [Mni[3]]
                if len(lam) > 3:
                    lami_flat += lam[3] if isinstance(lam[3], list) else [lam[3]]

                # Initialize lists
                lam_flat = [lamf] * len(Mni_flat)
                Mn_flat = [Mn] * len(Mni_flat)

                # Create DataFrame for plotting
                data = pd.DataFrame({
                    "Lambda Flange i (width-to-thickness ratio)": lami_flat,
                    "Lambda Flange (width-to-thickness ratio)": lam_flat,
                    "Mni (Moment, t-m)": Mni_flat,
                    "Mn (Moment, t-m)": Mn_flat
                })

                # Ensure valid x-axis column
                fig = px.line(
                    data, x="Lambda Flange i (width-to-thickness ratio)", 
                    y=["Mni (Moment, t-m)", "Mn (Moment, t-m)"],
                    title="Nominal Moment (Mn) vs. Lambda Flange",
                    labels={"Lambda Flange i (width-to-thickness ratio)": "Width-to-Thickness Ratio",
                            "Mni (Moment, t-m)": "Moment (t-m)",
                            "Mn (Moment, t-m)": "Moment (t-m)"}
                )

                # Check if Lb exists before adding vline
                if "Lb" in locals() or "Lb" in globals():
                    fig.add_vline(x=Lb, line=dict(color="red", dash="dot"), 
                                annotation_text="Lb", annotation_position="top")

                # Update layout
                fig.update_layout(
                    xaxis_title="Width-to-Thickness Ratio",
                    yaxis_title="Nominal Moment (Mn)"
                )

                st.plotly_chart(fig)

            except Exception as e:
                st.error(f"Error in plotting: {e}")

with tab3:
    data = pd.read_csv(file_path)
    # User input for filtering Zx [cm³]
    zx_min = st.number_input("Show values greater than or equal to Zx [cm3]:", min_value=0, value=0, step=10)

    # Apply filtering: Show only rows where "Zx [cm³]" is greater than or equal to zx_min
    filtered_data = data[data["Zx [cm3]"] >= zx_min]

    # Configure AgGrid to allow multiple row selection
    gb = GridOptionsBuilder.from_dataframe(filtered_data)
    gb.configure_selection("multiple", use_checkbox=True)  # Enable multi-select with checkboxes
    gb.configure_grid_options(enableCellTextSelection=True)
    grid_options = gb.build()

    # Display AgGrid
    grid_response = AgGrid(
        filtered_data,
        gridOptions=grid_options,
        height=300,
        width="100%",
        theme="streamlit"
    )

    # Get selected rows data
    selected_rows = grid_response["selected_rows"]
    df_Selected = pd.DataFrame(selected_rows)

    # Display selected data
    st.write("Selected Rows Data:")
    st.write(selected_rows)
    st.write(len(df_Selected))

with tab4:
    # Display the appropriate input widget
    if st.session_state.input_mode == "slider":
        Lbd = st.slider("Input Unbraced Length (Lb).", 0, 20)
    else:
        Lbd = st.number_input("Input Unbraced Length (Lb).")
    st.write("The current number is:", Lbd)
   
    if df_Selected is None or df_Selected.empty:
        st.error("No data available in df_Selected.")
        st.stop()

    # Create tabs for each selected section
    if 'Section' in df_Selected.columns:
        section_names = df_Selected["Section"].unique()
    else:
        print("The 'Section' column is missing.")
    
    tabsp = []
    for section in section_names:
        tab_title = f"Results for {section}"
        tab_content = data.get(section)  # Assuming `data` is a dictionary or similar structure
        if not tab_content:  # Check if the data for this section is empty or None
            tab_content = "No Data Available"
        tabsp.append(st.tab(tab_title, tab_content))

    # Use `tabs` to display them in Streamlit
    st.tabs(tabsp)


    for idx, section in enumerate(section_names):
        with tabsp[idx]:
            # Filter rows for the current section
            section_data = df_Selected[df_Selected["Section"] == section]
            colc = st.columns([2,4])
            # Calculate values and display table for the selected section
            with colc[0]:
                with st.expander(f"Results Table for Section {section}"):
                    try:
                        Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat=df_mat, option=section, option_mat=option_mat, Lb=Lbd)
                        Fib = 0.9
                        FibMn = 0.9 * Mn

                        # Create DataFrame for results
                        result_data = {
                            "Parameter": ["Mn (t-m.)", "Lb (m.)", "Lp (m.)", "Lr (m.)", "Mp (t-m.)", "Case", "Fib", "FibMp (t-m.)"],
                            "Value": [Mn, Lb, Lp, Lr, Mp, Case, Fib, FibMn]
                        }
                        result_df = pd.DataFrame(result_data)
                        st.write(f"Results for Section {section}:")
                        st.dataframe(result_df)

                    except Exception as e:
                        st.error(f"Error in calculation for section {section}: {str(e)}")

            with colc[1]:
                # Plotting data for the current section
                with st.expander(f"Plot for Section {section}"):
                    try:
                        # Flatten the nested lists for plotting
                        Mni_flat = Mni[:3] + Mni[3]
                        Lni_flat = Lni[:3] + Lni[3]

                        # Initialize flat lists
                        Lb_flat = []
                        Mn_flat = []

                        # Create lists for Lb_flat and Mn_flat
                        for i in range(len(Mni_flat)):
                            Lb_flat.append(Lb)  # Assuming Lb is a constant
                            Mn_flat.append(Mn)  # Assuming Mn is a constant

                        # Convert data to a pandas DataFrame for plotting
                        data = pd.DataFrame({
                            "Lni (Length, m)": Lni_flat,
                            "Lb (Length, m)": Lb_flat,
                            "Mni (Moment, t-m)": Mni_flat,
                            "Mn (Moment t-m)": Mn_flat,
                        })

                        # Plot the graph using Plotly Express
                        fig = px.line(data, x="Lni (Length, m)", y=["Mni (Moment, t-m)", "Mn (Moment t-m)"],
                                    title=f"Nominal Moment (Mn) vs. Unbraced Length (Lb) for {section}",
                                    labels={"Lni (Length, m)": "Length (m)",
                                            "Mni (Moment, t-m)": "Moment (t-m)",
                                            "Mn (Moment t-m)": "Moment (t-m)"})

                        # Add vertical line for Lb (constant)
                        fig.add_vline(x=Lb, line=dict(color="red", dash="dot"), 
                                    annotation_text="Lb", annotation_position="top")

                        # Add axis titles using update_layout
                        fig.update_layout(
                            xaxis_title="Unbraced Length (Lb)",  # Title for the x-axis
                            yaxis_title="Nominal Moment (Mn)",  # Title for the y-axis
                        )

                        st.plotly_chart(fig)

                    except Exception as e:
                        st.error(f"Error in plotting for section {section}: {str(e)}")