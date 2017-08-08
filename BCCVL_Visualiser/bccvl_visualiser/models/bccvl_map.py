import mapscript
import csv
from mapscript import mapObj, OWSRequest
import logging
import os
import threading
import sys

import hashlib

from bccvl_visualiser.models.external_api.data_mover import FDataMover

import gdal
from gdalconst import GA_ReadOnly
import string

class BCCVLMap(mapObj):
    """ Our custom BCCVL mapObj.

        Provides additional utitlity functions on top of
        mapscript's mapObj class
    """

    MAPSCRIPT_RLOCK = threading.RLock()
    MAP_FILES_ROOT_PATH      = None
    MAP_DATA_FILES_ROOT_PATH = None

    DEFAULT_LAYER_NAME = 'DEFAULT'

    EXTENSION = ''
    DEAFULT_MAP_FILE_NAME = 'default.map'

    @classmethod
    def configure_from_config(class_, settings):
        """ configure the BCCVL Map constants """
        log = logging.getLogger(__name__)

        if (class_.MAP_FILES_ROOT_PATH is not None) or (class_.MAP_DATA_FILES_ROOT_PATH is not None):
            log.warn("Warning, %s is already configured. Ignoring new configuration.", str(class_))
            return

        class_.MAP_FILES_ROOT_PATH      = settings['bccvl.mapscript.map_files_root_path']
        class_.MAP_DATA_FILES_ROOT_PATH = settings['bccvl.mapscript.map_data_files_root_path']

    def __init__(self, map_file_name=None, data_id=None, data_url=None, layer_name=None, query_string=None, **kwargs):
        """ initialise the map instance from a data_url """

        if data_id and data_url:
            raise ValueError("A BCCVLMap can't have both a data_id and a data_url")
        elif data_id:
            self._init_from_data_id(data_id)
        elif data_url:
            self._init_from_data_url(data_url)
        else:
            raise ValueError("A BCCVLMap must have a data_id or a data_url.")

        # If the user didn't override the map file name,
        # then use this class's default map file name
        if map_file_name is None:
            map_file_name = self.__class__.DEFAULT_MAP_FILE_NAME
        self.map_file_name = map_file_name

        # If the user didn't override the layer name,
        # then use this class's default layer name
        if layer_name is None:
            layer_name = self.__class__.DEFAULT_LAYER_NAME
        self.layer_name = layer_name

        self.map_file_path = self.__class__.get_map_file_path(map_file_name)

        super(BCCVLMap, self).__init__(self.map_file_path, **kwargs)

        self._set_map_defaults_if_not_set()
        self.set_ows_request_from_query_string(query_string)

    def _init_from_data_id(self, data_id):
        self.data_id = data_id
        raise NotImplementedError("data_id is not yet supported")

    def _init_from_data_url(self, data_url):
        """ initialise the map instance from a data_url """
        self.data_url = data_url

        # generate a hash of the url
        hash_string = hashlib.sha224(self.data_url).hexdigest()

        self.file_name = hash_string + self.__class__.EXTENSION
        self.data_file_path = self.__class__.get_path_to_map_data_file(self.file_name)

        with self.__class__.MAPSCRIPT_RLOCK:
            if not os.path.isfile(self.data_file_path):
                self._download_data_to_file()

    def set_ows_request_from_query_string(self, query_string):
        log = logging.getLogger(__name__)
        ows_request = OWSRequest()

        # loadParamsFromURL causes a seg fault if passed an empty string.
        # Don't pass it an empty string...
        if ( ( type(query_string) == str ) and ( query_string.strip() != '' ) ):
            ows_request.loadParamsFromURL(query_string)

        if (ows_request.getValueByName('LAYER') is None):
            ows_request.addParameter('LAYER', self.layer_name)
            log.debug("Setting OWS paramater LAYER as not already set. Set to: %s", self.layer_name)

        if (ows_request.getValueByName('LAYERS') is None):
            ows_request.addParameter('LAYERS', self.layer_name)
            log.debug("Setting OWS paramater LAYERS as not already set. Set to: %s", self.layer_name)

        self.ows_request = ows_request

    def _download_data_to_file(self):
        log = logging.getLogger(__name__)
        mover = FDataMover.new_data_mover(self.data_file_path, data_url = self.data_url)

        # Make sure only one thread is trying to check for
        # the existance of, or trying to write the file
        # at any time.
        with self.__class__.MAPSCRIPT_RLOCK:
            mover.move_and_wait_for_completion()

            valid, problems = self._validate_file()
            if not valid:
                log.info("Deleting invalid file: %s", self.data_file_path)
                # Delete the file
                os.remove(self.data_file_path)
                raise ValueError("Problem validating file. Problems: %s" % (problems))


    def _validate_file(self):
        """ Validate the file

            Return if the file is valid (True/False),
            and return a list of problems (empty if no problems).
        """

        return True, []

    @classmethod
    def get_path_to_map_data_file(class_, data_file_name):
        log = logging.getLogger(__name__)

        map_data_files_root_path = class_.MAP_DATA_FILES_ROOT_PATH

        return_value = os.path.join(map_data_files_root_path, data_file_name)

        log.debug('Map data files root path: %s', map_data_files_root_path)
        log.debug('Map data file path: %s', return_value)

        return return_value

    @classmethod
    def get_map_file_path(class_, map_file_name):
        """ Returns the full os system path to the mapfile

            Uses the application config
            to look up the root map files path (where the map files are stored),
            and then joins this with the provided map_file_name argument.

        """

        log = logging.getLogger(__name__)

        map_files_root_path = class_.MAP_FILES_ROOT_PATH

        return_value = os.path.join(map_files_root_path, map_file_name)

        log.debug('Map files root path: %s', map_files_root_path)
        log.debug('Map file path: %s', return_value)

        return return_value

    def _set_map_defaults_if_not_set(self):
        """ Default the map's attributes """
        log = logging.getLogger(__name__)

        # Default the map attributes:
        #   * shapepath: the path to data files
        if self.shapepath == None:
            map_data_files_root_path = self.__class__.MAP_DATA_FILES_ROOT_PATH
            log.debug("Setting mapObj.shapepath as not already set. Set to: %s", map_data_files_root_path)
            self.shapepath = map_data_files_root_path


    def render(self):
        """ Render this map object

            This will inspect the OWS request type, and render the correct image
            for the request.

            Known supported OWS REQUEST values:

            * GetLegendGraphic: Will render the legend for the OWS request
            * GetMap: Will render the map tile for the OWS request
        """

        log = logging.getLogger(__name__)

        content = None          # the bytes of the rendered image
        content_type = None     # the image mimetype
        retval = None           # the OWS return value, useful for debugging

        with self.__class__.MAPSCRIPT_RLOCK:
            try:
                ows_request_type = self.ows_request.getValueByName('REQUEST')

                if (ows_request_type == 'GetLegendGraphic'):
                    # Draw the legend for the map
                    retval = self.loadOWSParameters(self.ows_request)
                    image = self.drawLegend()
                    content = image.getBytes()
                    content_type = image.format.mimetype
                elif (ows_request_type == 'GetMap'):
                    # Draw the map (tiles)
                    retval = self.loadOWSParameters(self.ows_request)
                    image = self.draw()
                    content = image.getBytes()
                    content_type = image.format.mimetype
                else:
                    # Unexpected OWS request. Do our best to support it by
                    # falling back to using the OWS Dispatch

                    # Tell mapscript to start capturing the stdout in a buffer
                    mapscript.msIO_installStdoutToBuffer()
                    # dispatch the OWS request
                    retval = self.OWSDispatch(self.ows_request)
                    # Get the content type of the return value
                    content_type = mapscript.msIO_stripStdoutBufferContentType()
                    # Get the content of the resulting image
                    content = mapscript.msIO_getStdoutBufferBytes()

                if retval != mapscript.MS_SUCCESS:
                    # Failed to render the desired image
                    raise RuntimeError("Failed to render map OWS request")

            except:
                log.error("Error while trying to render map: %s", sys.exc_info()[0])
                raise
            finally:
                # Reset the mapscript I/O pointers back to where they should be
                mapscript.msIO_resetHandlers()

        return content, content_type, retval


class RasterBCCVLMap(BCCVLMap):
    DEFAULT_MAP_FILE_NAME = "default_raster.map"

    """ We assume the raster band of interest is band 1 """
    BAND_NUMBER = 1

    """ The metadata key used to identify the minimum expected value in the range """
    BCCVL_EXPECTED_VALUE_RANGE_MINIMUM_KEY = "BCCVL_EXPECTED_VALUE_RANGE_MINIMUM"
    """ The metadata key used to identify the maximum expected value in the range """
    BCCVL_EXPECTED_VALUE_RANGE_MAXIMUM_KEY = "BCCVL_EXPECTED_VALUE_RANGE_MAXIMUM"

    COLOR_BANDS = 8
    MIN_COLOR = [255, 255, 255]
    MAX_COLOR = [128, 0,   255]

    def __init__(self, **kwargs):
        super(RasterBCCVLMap, self).__init__(**kwargs)
        self._set_style_information()

    def _set_style_information(self):
        """ Programatically define the style and legend information

            This function walks between the MIN_COLOR and MAX_COLOR.
            It applies the MIN_COLOR to the minimum expected value in the raster,
            and it applies the MAX_COLOR to the maximum expected value in the raster.

            Between the minimum and the maximum, it walks COLOR_BANDS steps.

            The legend will consist of COLOR_BANDS + 1 levels in total.
            The min to max will be walked in COLOR_BANDS steps. At each
            step, the minimum of the step is shown in the legend. After these steps
            we add the maximum value to the legend as a 'point' value (not a range).

            Example: 2 COLOR_BANDS, with min_exp = 0, and max_exp = 1

                0    ( colors 0.0 - 0.5 )
                0.5  ( colors 0.5 - 1.0 )
                1    ( colors 1.0       )

        """

        # Get the expected value range
        min_exp, max_exp = self.get_expected_value_range()
        min_exp = float(min_exp)
        max_exp= float(max_exp)

        # Get the map layer
        layer = self.getLayerByName(self.layer_name)

        # Calc. the range of expected values
        the_range = (max_exp - min_exp)

        # Work out a value to increment across the range (We want COLOR_BANDS color bands)
        the_inc = the_range / float(self.__class__.COLOR_BANDS)

        # Grab a handle to the min/max color
        min_color = self.__class__.MIN_COLOR
        max_color = self.__class__.MAX_COLOR

        # Calc. the range the r/g/b colors will pass
        r_color_diff = max_color[0] - min_color[0]
        g_color_diff = max_color[1] - min_color[1]
        b_color_diff = max_color[2] - min_color[2]

        # The next color we will draw is the first color
        next_color_r = min_color[0]
        next_color_g = min_color[1]
        next_color_b = min_color[2]

        val = min_exp
        while val < max_exp:

            # This color is the 'next' color (our old next)
            this_color_r = next_color_r
            this_color_g = next_color_g
            this_color_b = next_color_b

            this_color = ' '.join(map(str, [this_color_r, this_color_g, this_color_b]))

            # Calc. the next color along
            next_color_r = min_color[0] + ( r_color_diff * ( (val+the_inc-min_exp) / float(the_range)) )
            next_color_g = min_color[1] + ( g_color_diff * ( (val+the_inc-min_exp) / float(the_range)) )
            next_color_b = min_color[2] + ( b_color_diff * ( (val+the_inc-min_exp) / float(the_range)) )

            next_color = ' '.join(map(str, [next_color_r, next_color_g, next_color_b]))

            self.__class__._update_range_style_information(layer, val, val+the_inc, this_color, next_color, max_exp)
            # inc the value
            val = val + the_inc

        # Add the max value to the legend
        self.__class__._update_max_style_information(layer, max_exp)

    @classmethod
    def _update_max_style_information(_class, layer, max_exp):
        style_template = string.Template("""\
CLASSITEM "[pixel]"
    CLASS
        NAME "${max_exp}"
        EXPRESSION ([pixel]=${max_exp})
        STYLE
            COLOR $max_color
        END
    END
END
""")
        style_string = style_template.substitute(
            max_exp=max_exp,
            max_color=' '.join(map(str, _class.MAX_COLOR))
        )

        layer.updateFromString(style_string)

    @classmethod
    def _update_range_style_information(_class, layer, lower_bound, upper_bound, lower_bound_color, upped_bound_color, max_value):
        style_template = string.Template("""\
CLASSITEM "[pixel]"
    CLASS
        NAME "${lower_bound}"                       # name in legend is the min value of the range
        EXPRESSION ([pixel]>${lower_bound} AND [pixel]<=${upper_bound})
        STYLE
            COLOR $lower_bound_color                # show the legend's color as the min value in the range.
            COLORRANGE  ${lower_bound_color} ${upped_bound_color}
            DATARANGE   ${lower_bound} ${upper_bound}
        END
    END
END
""")
        style_string = style_template.substitute(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            lower_bound_color=lower_bound_color,
            upped_bound_color=upped_bound_color,
        )

        layer.updateFromString(style_string)

    def _set_map_defaults_if_not_set(self, **kwargs):
        """ Default the map's attributes """
        super(RasterBCCVLMap, self)._set_map_defaults_if_not_set(**kwargs)

        log = logging.getLogger(__name__)

        # Default the layer attributes:
        #   * data: the file path relative to shape path
        layer = self.getLayerByName(self.layer_name)
        if layer != None and layer.data == None:
            log.debug("Setting mapObj.layer.data as not already set. Set to: %s", self.file_name)
            layer.data = self.file_name

    def get_gdal_dataset(self, mode=GA_ReadOnly):
        """ For advanced users only. Returns the gdal_dataset for this file.

            By default, the file is opened in a read-only mode.
        """
        dataset = gdal.Open(self.data_file_path, mode)
        return dataset

    def get_minimum_value(self):
        """ Get the minimum value in the raster """

        band_number = self.__class__.BAND_NUMBER
        dataset = self.get_gdal_dataset()
        if dataset == None:
            raise ValueError("Failed to open data_file (%s) as a gdal dataset" % self.data_file_path)
        else:
            # Get the raster band
            band = dataset.GetRasterBand(band_number)
            the_min = band.GetMinimum()
            if the_min == None:
                # if the min isn't available directly, compute it
                (the_min, the_max) = band.ComputeRasterMinMax(band_number)
            # Return the minimum value
            return the_min

    def get_maximum_value(self):
        """ Get the maximum value in the raster """

        band_number = self.__class__.BAND_NUMBER
        dataset = self.get_gdal_dataset()
        if dataset == None:
            raise ValueError("Failed to open data_file (%s) as a gdal dataset" % self.data_file_path)
        else:
            # Get the raster band
            band = dataset.GetRasterBand(band_number)
            the_max = band.GetMaximum()
            if the_max == None:
                # if the max isn't available directly, compute it
                (the_min, the_max) = band.ComputeRasterMinMax(band_number)

            # Return the maximum value
            return the_max

    def get_expected_value_range(self):
        """ Determines a theoretical minimum and maximum _possible_ value for the original dataset.

            Note, this is different to the minimum and maximum value in the raster. This
            guesses, based on the maximum value found in the raster, what the possible
            maximum value was when generating the file.

            If metadata is avaialble in the file, the metadata is used. The metadata
            is first checked at the band level. The file level is then checked as a
            fallback.

                BCCVL_EXPECTED_VALUE_RANGE_MINIMUM: The minimum value in the range.
                BCCVL_EXPECTED_VALUE_RANGE_MAXIMUM: The maximum value in the range.

            If no metadata is available, the range is 'guessed'.

            If a file is found to have a maximum value < 1, the file is assumed
            to be of the range 0 to 1.

            If a file is found to have a maximum value > 1, the max value in the file is assumed.
        """
        min_value_metadata_key = self.__class__.BCCVL_EXPECTED_VALUE_RANGE_MINIMUM_KEY
        max_value_metadata_key = self.__class__.BCCVL_EXPECTED_VALUE_RANGE_MAXIMUM_KEY

        value_range_min = None
        value_range_max = None
        band_metadata = self.get_band_metadata()
        file_metadata = self.get_metadata()

        # Determine the minimum expected value
        #
        # check the band metadata
        if min_value_metadata_key in band_metadata:
            value_range_min = band_metadata[min_value_metadata_key]
        # check the file level metadata
        elif min_value_metadata_key in file_metadata:
            value_range_min = file_metadata[min_value_metadata_key]
        # finally, guess
        else:
            # if the minimum is lower than 0, we have no idea what is going on.
            # let the minimum be the minimum in the file
            if self.get_minimum_value() < 0:
                value_range_min = self.get_minimum_value()
            else:
                value_range_min = 0

        # Determine the maximum expected value
        #
        # check the band metadata
        if max_value_metadata_key in band_metadata:
            value_range_max = band_metadata[max_value_metadata_key]
        # check the file level metadata
        elif max_value_metadata_key in file_metadata:
            value_range_max = file_metadata[max_value_metadata_key]
        # finally, guess
        else:
            # if the maximum is over 1, we have no idea what is going on.
            # let the maximum be the maximum in the file
            if self.get_maximum_value() > 1:
                value_range_max = self.get_maximum_value()
            # if value is < 1, assume max value is 1 (as is the case for dismo)
            else:
                value_range_max = 1

        return value_range_min, value_range_max

    def get_metadata(self):
        """ Returns the metadata available at the file level """
        dataset = self.get_gdal_dataset()
        return dataset.GetMetadata()

    def get_band_metadata(self):
        """ Returns the metadata available at the band level """
        band_number = self.__class__.BAND_NUMBER
        dataset = self.get_gdal_dataset()
        band = dataset.GetRasterBand(band_number)
        return band.GetMetadata()

    def get_scale(self):
        """ Get the scale of the raster """

        band_number = self.__class__.BAND_NUMBER
        dataset = self.get_gdal_dataset()
        if dataset == None:
            raise ValueError("Failed to open data_file (%s) as a gdal dataset" % self.data_file_path)
        else:
            # Get the raster band
            band = dataset.GetRasterBand(band_number)
            # Return the scale
            return band.GetScale()

class GeoTiffBCCVLMap(RasterBCCVLMap):
    EXTENSION = ".tif"

class AsciiGridBCCVLMap(RasterBCCVLMap):
    EXTENSION = ".asc"

class OccurrencesBCCVLMap(BCCVLMap):
    EXTENSION = ".csv"
    DEFAULT_MAP_FILE_NAME = "default_occurrences.map"

    LNG_COLUMN_NAME = 'lon'
    LAT_COLUMN_NAME= 'lat'

    class OccurrencesDialect(csv.Dialect):
        strict = True
        skipinitialspace = True
        quoting = csv.QUOTE_MINIMAL
        delimiter = ','
        quotechar = '"'
        lineterminator = '\n'

    def __init__(self, **kwargs):
        super(OccurrencesBCCVLMap, self).__init__(**kwargs)
        self.set_connection_for_map_connection_if_not_set()

    def set_connection_for_map_connection_if_not_set(self):
        class_ = self.__class__
        lng_column = class_.LNG_COLUMN_NAME
        lat_column = class_.LAT_COLUMN_NAME

        log = logging.getLogger(__name__)

        layer = self.getLayerByName(self.layer_name)

        if layer != None and layer.connection == None:
            connection = self._get_connection(lng_column, lat_column)
            log.debug("Setting map layer connection to: %s", connection)
            layer.connection = connection

    def _get_connection(self, x_column_name='lon', y_column_name='lat'):
        connection = """"\
<OGRVRTDataSource>
    <OGRVRTLayer name='{0}'>
        <SrcDataSource>{1}</SrcDataSource>
        <LayerSRS>WGS84</LayerSRS>
        <GeometryField encoding='PointFromColumns' x='{2}' y='{3}'/>
        <GeometryType>wkbPoint</GeometryType>
    </OGRVRTLayer>
</OGRVRTDataSource>""".format(os.path.splitext(self.file_name)[0], self.data_file_path, x_column_name, y_column_name)

        return connection

    def _validate_file(self):
        class_ = self.__class__
        lng_column = class_.LNG_COLUMN_NAME
        lat_column = class_.LAT_COLUMN_NAME

        log = logging.getLogger(__name__)

        try:
            valid, problems = class_._check_if_occurrences_csv_valid(self.data_file_path, lng=lng_column, lat=lat_column)
        except:
            log.error("Error validating the file: %s", sys.exc_info()[0])
            return False, [ "Error validating the file: %s" % sys.exc_info()[0] ]

        return valid, problems

    @classmethod
    def _check_if_occurrences_csv_valid(class_, file_path, lng='lon', lat='lat', limit=10):
        """ Determines if the CSV is valid or not

            If an invalid CSV is processed via mapscript, a seg fault is likely to
            occur. For this reason, it is important that the file be FULLY validated
            before it is first used.

        """
        log = logging.getLogger(__name__)

        field_names = []
        problems = []

        with class_.MAPSCRIPT_RLOCK:
            with open(file_path, 'rb') as csvfile:
                reader = csv.reader(csvfile, class_.OccurrencesDialect)
                field_names = reader.next()

                # Ensure that the expected latitude and longitude columns are in the
                # list of expected field_names
                if not (lng in field_names):
                    log.warn("CSV (%s) doesn't contain a '%s' column", file_path, lng)
                    problems.append("CSV (%s) doesn't contain a '%s' column" % (file_path, lng))
                    return False, problems
                elif not (lat in field_names):
                    problems.append("CSV (%s) doesn't contain a '%s' column" % (file_path, lat))
                    log.warn("CSV (%s) doesn't contain a '%s' column", file_path, lat)
                    return False, problems

                num_cols = len(field_names)

                lng_position = field_names.index(lng)
                lat_position = field_names.index(lat)

                # Iterate over each remaining row in the csv reader (we've already processed
                # the header)
                for row in reader:
                    # Check that the row has the correct number of columns
                    if len(row) != num_cols:
                        problems.append("CSV (%s) contains different length rows: %s" % (file_path, rows))

                    # Check that the row has a valid lng
                    lng_s = row[lng_position]
                    try:
                        lng_f = float(lng_s)
                    except:
                        problems.append("CSV (%s) contains an invalid %s: %s" % (file_path, lng, lng_s))

                    # Check that the row has a valid lat
                    lat_s = row[lat_position]
                    try:
                        lat_f = float(lat_s)
                    except:
                        problems.append("CSV (%s) contains an invalid %s: %s" % (file_path, lat, lat_s))

                    # Only provide info on at most +limit+ problems
                    if limit and ( len(problems) >= limit ):
                        break

        valid = ( len(problems) == 0 )
        return valid, problems
